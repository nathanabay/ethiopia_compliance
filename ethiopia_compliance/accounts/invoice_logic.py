import frappe
from frappe import _

def validate_fs_number(doc, method):
    if doc.docstatus == 1 and not doc.custom_fs_number:
        frappe.msgprint(_("Warning: FS Number (Fiscal Signature) is missing."), indicator='orange')
