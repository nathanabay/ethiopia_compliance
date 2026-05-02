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
	"""
	# 1. Check if integration is enabled
	settings = frappe.get_cached_doc("Compliance Setting")
	if not settings.get("enable_fiscal_device"):
		return

	# Skip if already registered (idempotent)
	if doc.custom_fs_number and doc.custom_fiscal_machine_no:
		return

	api_endpoint = (settings.get("fiscal_device_api_endpoint") or "").strip()
	device_type = (settings.get("fiscal_device_type") or "").strip()
	serial = (settings.get("device_serial_number") or "").strip()

	if not api_endpoint:
		frappe.msgprint(
			_("Fiscal device is enabled but no API endpoint is configured in Compliance Setting."),
			indicator="orange", alert=True
		)
		return

	# 2. Construct payload
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

	# 3. Call fiscal device API
	# -------------------------------------------
	# NexGo devices: HTTP POST with HMAC-SHA256 signed JSON-RPC payload.
	# EFD devices: proprietary binary protocol over TCP socket (requires pyserial).
	#
	# Retry policy: up to 3 attempts with exponential backoff (1s, 2s, 4s).
	# Timeout per attempt: 30 seconds. On timeout or 5xx, retry.
	# On 4xx client error (bad payload), do NOT retry — inspect response and log.
	#
	# Required Compliance Setting fields:
	#   - fiscal_device_api_endpoint  (e.g. https://device.bespo.et/register)
	#   - fiscal_device_type          ("NexGo" or "EFD")
	#   - device_serial_number        (device MRC prefix)
	#   - device_secret_key           (HMAC signing secret — stored securely)
	# -------------------------------------------

	MAX_RETRIES = 3
	BACKOFF_SECS = [1, 2, 4]
	TIMEOUT_SECONDS = 30

	import time, hmac, hashlib, json as _json

	device_secret = (settings.get("device_secret_key") or "").strip()

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
						"Authorization": f"Bearer {settings.get('fiscal_device_api_key', '')}",
						"Content-Type": "application/json",
						"X-Device-Type": device_type,
						"X-Device-Serial": serial,
					},
					timeout=TIMEOUT_SECONDS
				)
				if response.status_code >= 500:
					# Server-side error — retry with backoff
					time.sleep(BACKOFF_SECS[attempt])
					continue
				if response.status_code >= 400:
					# Client error — log and do not retry
					frappe.log_error(
						title="Fiscal Device Client Error",
						message=f"Status: {response.status_code} | Body: {response.text[:500]}"
					)
					response.raise_for_status()
				# Success
				return response.json()
			except requests.exceptions.Timeout:
				frappe.log_error(title="Fiscal Device Timeout", message=f"Attempt {attempt + 1}/{MAX_RETRIES}")
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
			message=str(e)
		)
		frappe.throw(
			_("Failed to register invoice with fiscal device: {0}").format(str(e))
		)

	# 4. Stamp the FS Number and MRC onto the document
	doc.custom_fs_number = fs_number
	doc.custom_fiscal_machine_no = mrc

	frappe.msgprint(
		_("Fiscal device registered — FS No: {0}, MRC: {1}").format(fs_number, mrc),
		indicator="green", alert=True
	)
