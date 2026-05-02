import frappe
from frappe import _

FS_REQUIRED_THRESHOLD = 50000  # Proclamation No. 1395/2025 — mandatory FS Number >= 50,000 ETB

def validate_fs_number(doc, method):
	"""Validate FS Number is present before submitting Sales Invoice.

	- Grand Total >= 50,000 ETB: mandatory, blocks submission (frappe.throw)
	- Grand Total < 50,000 ETB: warns but allows submission (frappe.msgprint)

	Hooked to Sales Invoice before_submit via hooks.py.
	"""
	if not doc.custom_fs_number:
		if doc.grand_total >= FS_REQUIRED_THRESHOLD:
			frappe.throw(
				_("FS Number (Fiscal Signature) is mandatory for transactions of 50,000 ETB or more. "
				  "Please enter an FS Number before submitting.")
			)
		else:
			frappe.msgprint(
				_("Warning: FS Number (Fiscal Signature) is missing. This is recommended for tax compliance."),
				indicator='orange'
			)
