# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Compliance Audit Log DocType

Tracks all TIN validation API calls and any manual overrides
performed by users. Provides a complete audit trail for tax
compliance reviews.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import now, getdate, now_datetime


class ComplianceAuditLog(Document):
    """Audit log for TIN validation API calls and manual overrides.

    Created automatically by tin_validator.py and other compliance modules.
    Do not delete or modify manually — all records are append-only.
    """

    def before_insert(self):
        if not self.log_timestamp:
            self.log_timestamp = now_datetime()

    def validate(self):
        """Ensure critical fields are populated."""
        if not self.event_type:
            frappe.throw(_("Event Type is required."))
        if not self.entity_type:
            frappe.throw(_("Entity Type is required."))
        if not self.entity_name:
            frappe.throw(_("Entity Name is required."))


@frappe.whitelist()
def log_tin_validation(entity_type, entity_name, tin_number,
                        validation_result, override_performed=False,
                        override_by=None, override_reason=None):
    """Create an audit log entry for a TIN validation event.

    Args:
        entity_type (str): Supplier | Customer | Employee
        entity_name (str): Name of the entity
        tin_number (str): TIN that was validated
        validation_result (dict): Result from validate_tin()
        override_performed (bool): Whether a manual override was applied
        override_by (str): User who performed the override
        override_reason (str): Reason for the override

    Returns:
        ComplianceAuditLog: the created log document
    """
    log = frappe.new_doc("Compliance Audit Log")
    log.event_type = "TIN Validation"
    log.entity_type = entity_type
    log.entity_name = entity_name
    log.tin_number = tin_number
    log.validation_result = str(validation_result)
    log.override_performed = 1 if override_performed else 0
    log.override_by = override_by
    log.override_reason = override_reason
    log.user = frappe.session.user
    log.insert(ignore_permissions=True)
    return log


@frappe.whitelist()
def log_wht_application(purchase_invoice, supplier, wht_rate,
                        wht_amount, penalty_applied=False):
    """Create an audit log entry for a WHT deduction event.

    Args:
        purchase_invoice (str): Purchase Invoice name
        supplier (str): Supplier name
        wht_rate (float): Applied WHT rate
        wht_amount (float): WHT amount deducted
        penalty_applied (bool): Whether punitive 30% rate was used

    Returns:
        ComplianceAuditLog: the created log document
    """
    log = frappe.new_doc("Compliance Audit Log")
    log.event_type = "WHT Applied"
    log.entity_type = "Supplier"
    log.entity_name = supplier
    log.reference_doctype = "Purchase Invoice"
    log.reference_name = purchase_invoice
    log.tax_rate = wht_rate
    log.tax_amount = wht_amount
    log.override_performed = 1 if penalty_applied else 0
    log.user = frappe.session.user
    log.insert(ignore_permissions=True)
    return log


@frappe.whitelist()
def log_cash_transaction_blocked(doc_name, amount, mode_of_payment,
                                   reason):
    """Create an audit log entry for a blocked cash transaction.

    Args:
        doc_name (str): Payment Entry or Journal Entry name
        amount (float): Transaction amount
        mode_of_payment (str): Mode of payment used
        reason (str): Blocking reason / proclamation reference

    Returns:
        ComplianceAuditLog: the created log document
    """
    log = frappe.new_doc("Compliance Audit Log")
    log.event_type = "Cash Transaction Blocked"
    log.entity_type = "Payment Entry"
    log.entity_name = doc_name
    log.tax_amount = amount
    log.override_performed = 0
    log.notes = f"Mode: {mode_of_payment} | Reason: {reason}"
    log.user = frappe.session.user
    log.insert(ignore_permissions=True)
    return log