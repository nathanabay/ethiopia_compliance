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
	# TODO: Replace this mock with actual vendor API call.
	# NexGo devices typically expect a signed JSON-RPC call.
	# EFD devices use a proprietary binary protocol over TCP.
	# The actual implementation depends on the vendor SDK contract.
	#
	# Example (NexGo):
	#   response = requests.post(
	#       api_endpoint,
	#       json=payload,
	#       headers={"Authorization": "Bearer <api_key>", "Content-Type": "application/json"},
	#       timeout=30
	#   )
	#   result = response.json()
	# -------------------------------------------

	try:
		# Mock: simulate a successful fiscal device registration
		# Generates a placeholder FS Number in the format FISCAL-YYYYMMDD-XXXX
		import random
		from datetime import date
		today_str = date.today().strftime("%Y%m%d")
		suffix = str(random.randint(1000, 9999))
		fs_number = f"FISCAL-{today_str}-{suffix}"
		mrc = (serial or "EFD-DEFAULT").upper()

		# Simulate network latency
		# import time; time.sleep(0.2)

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
