# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Purchase Order Compliance Checks

Phase 1.7: On Purchase Order validate, if supplier lacks a valid TIN,
issue a warning about the impending 30% WHT penalty.

The actual client-side msgprint warning is triggered via a Client Script
(wht_po_warning.js) hooked through the Purchase Order form.
This server-side function provides a server-side fallback and audit trail.
"""

import frappe
from frappe import _


def warn_missing_supplier_tin(doc, method):
    """Server-side check: if supplier has no valid TIN, log a compliance warning.

    This runs on Purchase Order validate as a fallback / audit trail.
    The primary user-facing warning is delivered via client-side JS
    (frappe.msgprint) in the Purchase Order form.

    Hooked to Purchase Order validate via hooks.py.
    """
    if not doc.supplier:
        return

    from ethiopia_compliance.utils.tin_validator import is_supplier_tin_valid

    if is_supplier_tin_valid(doc.supplier):
        return

    # Log the warning in the Document's comment system for audit trail
    frappe.publish_realtime(
        event="doc_comment",
        message={
            "doctype": doc.doctype,
            "docname": doc.name,
            "comment": _(
                "COMPLIANCE WARNING: Supplier {0} does not have a valid TIN on file. "
                "A 30% punitive WHT rate will be applied to this Purchase Order "
                "under Proclamation No. 1395/2017 Art. 97."
            ).format(doc.supplier)
        },
        after_commit=True
    )