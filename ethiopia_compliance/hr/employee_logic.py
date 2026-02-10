import frappe
from frappe import _

def validate_employee(doc, method):
    if doc.tax_id:
        clean_tin = doc.tax_id.replace("-", "").replace(" ", "").strip()
        if not clean_tin.isdigit() or len(clean_tin) != 10:
            frappe.throw(_("Ethiopian TIN must be exactly 10 digits."))
        doc.tax_id = clean_tin
        if not doc.custom_pension_number:
            doc.custom_pension_number = clean_tin
