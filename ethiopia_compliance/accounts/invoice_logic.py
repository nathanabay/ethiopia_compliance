import frappe
from frappe import _


def validate_fs_number(doc, method):
	"""Validate FS Number is present before submitting Sales Invoice.

	Hooked to Sales Invoice before_submit via hooks.py.
	"""
	if not doc.custom_fs_number:
		frappe.msgprint(
			_("Warning: FS Number (Fiscal Signature) is missing. This is recommended for tax compliance."),
			indicator='orange'
		)
