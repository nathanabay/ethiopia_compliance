import frappe
from frappe import _
from ethiopia_compliance.utils.tin_validator import validate_tin


def validate_employee(doc, method):
	"""Validate employee TIN and auto-clean format.

	Hooked to Employee validate via hooks.py.
	"""
	if doc.tax_id:
		# Clean the TIN value
		clean_tin = doc.tax_id.replace("-", "").replace(" ", "").strip()
		doc.tax_id = clean_tin

		# Validate using shared TIN validator
		result = validate_tin(clean_tin)
		if not result['valid']:
			frappe.throw(_(result['message']))
