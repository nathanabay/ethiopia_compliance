# Fiscal Device API Integration Framework
# Supports NexGo, EFD, and other Ethiopian fiscal printers
#
# TODO (vendor-specific):
#   - Inject cryptographic signing key per device type
#   - Replace mock POST with real API call per vendor SDK
#   - Add retry/timeout handling per device requirements
#   - Register MRC (Machine Registration Code) from device provisioning

import frappe
from frappe import _
from frappe.utils import flt, now_datetime


def register_sales_invoice(doc, method):
	"""Wired to Sales Invoice before_submit.

	If fiscal device integration is enabled, constructs the invoice payload,
	sends it to the fiscal device API, and stamps the returned FS Number
	and Fiscal Machine No onto the document.

	The actual HTTP call is deferred to a background job to avoid blocking
	document submission (max 90s potential latency from retries).
	"""
	# 1. Check if integration is enabled
	settings = frappe.get_cached_doc("Compliance Setting")
	if not settings.get("enable_fiscal_device"):
		return

	# Skip if already registered (idempotent)
	if doc.custom_fs_number and doc.custom_fiscal_machine_no:
		return

	api_endpoint = (settings.get("fiscal_device_api_endpoint") or "").strip()

	if not api_endpoint:
		frappe.throw(
			_("Fiscal device is enabled but no API endpoint is configured in Compliance Setting.")
		)

	# Defer HTTP call to background job to avoid blocking submission.
	# Credentials (device_secret, api_key) are NOT passed as enqueue args —
	# they are stored in site_config and read by the worker at runtime.
	# This prevents sensitive data from being serialized to the Redis queue.

	# Job deduplication: prevent double-enqueue if retry/submit happens quickly
	job_key = f"fiscal_device_{doc.name}"
	if not frappe.lock(job_key, timeout=300):
		return  # another job already pending for this invoice

	frappe.enqueue(
		"ethiopia_compliance.integrations.fiscal_device._register_sales_invoice_bg",
		invoice_name=doc.name,
		api_endpoint=api_endpoint,
		device_type=(settings.get("fiscal_device_type") or "").strip(),
		serial=(settings.get("device_serial_number") or "").strip(),
		queue="long",
		timeout=1200,
		on_failure=_fiscal_device_job_failed
	)


def _fiscal_device_job_failed(job, exc):
	"""Callback when fiscal device background job fails (M14 — silent failures fixed)."""
	frappe.log_error(
		title="Fiscal Device Background Job Failed",
		message=f"Invoice: {job.args.get('invoice_name', 'unknown')}\n\n"
		         f"Error: {exc}"
	)
	# Notify System Manager so failure isn't silent
	notify_users_with_role(
		"System Manager",
		_("Fiscal Device Registration Failed"),
		_("Background job failed for invoice {0}: {1}").format(
			job.args.get("invoice_name", "unknown"), exc
		)
	)


def notify_users_with_role(role, subject, message):
	"""Send notification to all users with a given role."""
	users = frappe.db.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		fields=["parent"]
	)
	for user_row in users:
		frappe.sendmail(
			recipients=[user_row.parent],
			subject=subject,
			message=message
		)


def _register_sales_invoice_bg(invoice_name, api_endpoint, device_type, serial):
	"""Background worker: register invoice with fiscal device and stamp FS Number.

	Credentials are read from site_config at runtime — never passed via enqueue args.
	"""
	# Read sensitive credentials from site_config (never serialized to Redis)
	device_secret = frappe.conf.get("fiscal_device_secret") or ""
	api_key = frappe.conf.get("fiscal_device_api_key") or ""

	doc = frappe.get_doc("Sales Invoice", invoice_name)

	# Construct payload
	items = []
	for item in doc.items:
		items.append({
			"item_code": item.item_code or "",
			"item_name": item.item_name or "",
			"qty": flt(item.qty, 4),
			"rate": flt(item.rate, 2),
			"amount": flt(item.amount, 2),
			"tax_amount": flt(item.get("tax_amount", 0), 2) if hasattr(item, "tax_amount") else 0
		})

	payload = {
		"invoice_number": doc.name,
		"posting_date": str(doc.posting_date),
		"customer_tin": doc.get("custom_customer_tin") or "",
		"customer_name": doc.customer_name or doc.customer,
		"grand_total": flt(doc.grand_total, 2),
		"total_taxes": flt(doc.total_taxes_and_charges, 2),
		"net_total": flt(doc.net_total or doc.total, 2),
		"items": items,
		"device_serial": serial,
		"device_type": device_type,
		"requested_at": str(now_datetime())
	}

	# Call fiscal device API
	# Retry policy: up to 3 attempts with exponential backoff (1s, 2s, 4s).
	# Timeout per attempt: 30 seconds.
	MAX_RETRIES = 3
	BACKOFF_SECS = [1, 2, 4]
	TIMEOUT_SECONDS = 30

	import time, hmac, hashlib, json as _json

	def _sign_payload(payload_dict, secret):
		"""Compute HMAC-SHA256 signature over JSON-serialized payload."""
		canonical = _json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
		return hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()

	def _call_device(payload):
		"""Make the HTTP call with retry/backoff. Returns response dict or raises."""
		import requests

		signed_payload = dict(payload)
		if device_secret:
			signed_payload["_signature"] = _sign_payload(payload, device_secret)

		for attempt in range(MAX_RETRIES):
			try:
				response = requests.post(
					api_endpoint,
					json=signed_payload,
					headers={
						"Authorization": f"Bearer {api_key}",
						"Content-Type": "application/json",
						"X-Device-Type": device_type,
						"X-Device-Serial": serial,
					},
					timeout=TIMEOUT_SECONDS
				)
				if response.status_code >= 500:
					time.sleep(BACKOFF_SECS[attempt])
					continue
				if response.status_code >= 400:
					frappe.log_error(
						title="Fiscal Device Client Error",
						message=f"Status: {response.status_code} | Body: {response.text[:500]}"
					)
					response.raise_for_status()
				return response.json()
			except requests.exceptions.Timeout:
				frappe.log_error(title="Fiscal Device Timeout",
					message=f"Attempt {attempt + 1}/{MAX_RETRIES} for {invoice_name}")
				if attempt < MAX_RETRIES - 1:
					time.sleep(BACKOFF_SECS[attempt])
				continue
			except requests.exceptions.RequestException as e:
				frappe.log_error(title="Fiscal Device Request Failed", message=str(e))
				if attempt < MAX_RETRIES - 1:
					time.sleep(BACKOFF_SECS[attempt])
				continue
		raise Exception(_("Fiscal device unreachable after {0} attempts").format(MAX_RETRIES))

	try:
		result = _call_device(payload)
		fs_number = result.get("fs_number") or result.get("receipt_no") or ""
		mrc = result.get("mrc") or result.get("machine_code") or serial or "EFD-DEFAULT"
		if not fs_number:
			raise Exception(_("Fiscal device response missing fs_number"))
	except Exception as e:
		frappe.log_error(
			title="Fiscal Device Registration Failed",
			message=f"Invoice {invoice_name}: {e}"
		)
		frappe.publish_realtime(
			"message",
			{"message": _("Fiscal device registration failed for {0}: {1}").format(invoice_name, str(e))},
			after_commit=True
		)
	finally:
		# Release deduplication lock (always)
		frappe.unlock(f"fiscal_device_{invoice_name}")
		return

	# Stamp the FS Number and MRC onto the document
	frappe.db.set_value("Sales Invoice", invoice_name, {
		"custom_fs_number": fs_number,
		"custom_fiscal_machine_no": mrc
	})

	frappe.publish_realtime(
		"message",
		{"message": _("Fiscal device registered — FS No: {0}, MRC: {1}").format(fs_number, mrc)},
		after_commit=True
	)
