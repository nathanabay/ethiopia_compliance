# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Automated WHT Certificate Generation

Proclamation No. 979/2016 Art. 97 as amended by Proclamation No. 1395/2017:
WHT certificates must be issued to suppliers within 15 days of the payment.

This module provides:
  - on_payment_submit(): triggered when a Payment Entry is submitted and
    references a Purchase Invoice that had WHT deducted.
  - It creates a WHT Certificate (wht_certificate) and emails the PDF
    to the supplier's contact email automatically.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, now_datetime
from frappe.utils.pdf import get_pdf


def on_invoice_submit(doc, method):
    """Trigger WHT certificate creation when a Purchase Invoice with WHT is submitted.

    Hooked to Purchase Invoice on_submit via hooks.py.
    This catches the invoice at point of booking (before payment).
    """
    if doc.docstatus != 1:
        return

    if not doc.supplier:
        return

    if not _invoice_has_wht(doc):
        return

    # Determine the posting date — use period from first of month
    period_to = getdate(doc.posting_date) or getdate(today())
    period_from = frappe.utils.get_first_day(period_to)

    # Check for existing draft certificate for this supplier/company/month
    existing = frappe.db.exists("WHT Certificate", {
        "supplier": doc.supplier,
        "company": doc.company,
        "period_from": period_from,
        "period_to": period_to,
        "docstatus": ["<", 1]
    })

    if existing:
        cert = frappe.get_doc("WHT Certificate", existing)
    else:
        cert = frappe.new_doc("WHT Certificate")
        cert.supplier = doc.supplier
        cert.company = doc.company
        cert.period_from = period_from
        cert.period_to = period_to
        cert.status = "Draft"
        cert.insert()

    _link_invoice_to_certificate(cert.name, doc.name, None)
    _email_wht_certificate(cert, doc.supplier)


def on_payment_submit(doc, method):
    """Automatically generate a WHT Certificate when a payment is submitted
    for a Purchase Invoice that has WHT applied.

    Hooked to Payment Entry on_submit via hooks.py.
    """
    if doc.payment_type != "Pay":
        return

    if not doc.references:
        return

    for ref in doc.references:
        if ref.reference_doctype != "Purchase Invoice":
            continue

        inv = _get_invoice_with_wht(ref.reference_name)
        if not inv:
            continue

        _create_wht_certificate_for_invoice(
            invoice_name=ref.reference_name,
            supplier=inv.supplier,
            company=doc.company,
            payment_entry=doc.name,
            posting_date=doc.posting_date
        )


WHT_KEYWORDS = frozenset({"withholding", "wht"})


def _matches_wht(description: str) -> bool:
    """Return True if description indicates a WHT tax row."""
    desc = (description or "").lower()
    return bool(WHT_KEYWORDS & set(desc.split())) or any(kw in desc for kw in WHT_KEYWORDS)


def _invoice_has_wht(invoice):
    """Return True if the purchase invoice has WHT applied."""
    return any(_matches_wht(t.description) for t in invoice.taxes)


def _get_invoice_with_wht(invoice_name):
    """Return a Purchase Invoice doc if it has WHT applied, else None."""
    if not frappe.db.exists("Purchase Invoice", invoice_name):
        return None

    inv = frappe.get_doc("Purchase Invoice", invoice_name)
    return inv if _invoice_has_wht(inv) else None


def _extract_wht_amount(invoice):
    """Extract total WHT amount from a Purchase Invoice's taxes."""
    return sum(flt(t.tax_amount) for t in invoice.taxes if _matches_wht(t.description))


def _create_wht_certificate_for_invoice(invoice_name, supplier, company,
                                         payment_entry, posting_date):
    """Create a WHT Certificate linked to the invoice and email it."""
    # Determine period_from/to — first day of month to payment date
    period_to = getdate(posting_date) or getdate(today())
    period_from = frappe.utils.get_first_day(period_to)

    # Check for existing draft certificate for this supplier/company/month
    existing = frappe.db.exists("WHT Certificate", {
        "supplier": supplier,
        "company": company,
        "period_from": period_from,
        "period_to": period_to,
        "docstatus": ["<", 1]  # Draft or submitted
    })
    if existing:
        cert = frappe.get_doc("WHT Certificate", existing)
    else:
        cert = frappe.new_doc("WHT Certificate")
        cert.supplier = supplier
        cert.company = company
        cert.period_from = period_from
        cert.period_to = period_to
        cert.status = "Draft"
        cert.insert()

    # Append invoice link if not already present
    _link_invoice_to_certificate(cert.name, invoice_name, payment_entry)

    # Submit the certificate so it's ready to send
    if cert.docstatus == 0:
        # Permission check: only System Manager or Accounts Manager can submit
        if "System Manager" in frappe.get_roles() or "Accounts Manager" in frappe.get_roles():
            cert.submit()
        else:
            frappe.throw(
                _("Only System Manager or Accounts Manager can submit WHT Certificate {0}").format(cert.name),
                title=_("Permission Denied")
            )

    # Email the PDF to supplier contact
    _email_wht_certificate(cert, supplier)


def _link_invoice_to_certificate(cert_name, invoice_name, payment_entry):
    """Add an invoice link row to the WHT Certificate if not already present."""
    cert = frappe.get_doc("WHT Certificate", cert_name)

    already_linked = any(
        d.invoice == invoice_name
        for d in cert.get("invoice_details", [])
    )
    if already_linked:
        return

    inv = frappe.get_doc("Purchase Invoice", invoice_name)
    wht_amount = _extract_wht_amount(inv)

    cert.append("invoice_details", {
        "invoice": invoice_name,
        "posting_date": inv.posting_date,
        "purchase_amount": flt(inv.base_net_total) if inv.base_net_total else flt(inv.total),
        "wht_deducted": abs(wht_amount)
    })

    # Recompute totals
    total_purchase = sum(
        flt(d.purchase_amount) for d in cert.invoice_details
    )
    total_wht = sum(
        flt(d.wht_deducted) for d in cert.invoice_details
    )
    cert.total_purchase_amount = total_purchase
    cert.total_wht_deducted = total_wht
    if total_purchase > 0:
        cert.wht_rate = flt((total_wht / total_purchase) * 100, 2)

    # Permission check before save
    if "System Manager" in frappe.get_roles() or "Accounts Manager" in frappe.get_roles():
        cert.save(ignore_permissions=True)
    else:
        frappe.throw(
            _("Only System Manager or Accounts Manager can update WHT Certificate {0}").format(cert.name),
            title=_("Permission Denied")
        )


def _email_wht_certificate(cert, supplier):
    """Generate PDF of the WHT Certificate and email it to the supplier.

    Args:
        cert: WHT Certificate document (submitted)
        supplier: Supplier name
    """
    try:
        # Get supplier contact email
        contact_email = _get_supplier_contact_email(supplier)
        if not contact_email:
            frappe.msgprint(
                _("WHT Certificate {0} was generated but no supplier "
                  "contact email was found — certificate not emailed.").format(cert.name),
                title=_("WHT Certificate — Email Skipped")
            )
            return

        # Generate PDF
        pdf_content = frappe.get_print(
            "WHT Certificate",
            cert.name,
            printer="WHT Certificate",
            html=None
        )

        # Build email
        subject = _("WHT Certificate {0} — {1}").format(cert.name, cert.supplier)
        message = _(
            "Dear {supplier_name},<br><br>"
            "Please find attached your Withholding Tax Certificate "
            "for the period {period_from} to {period_to}.<br><br>"
            "Certificate No: {cert_name}<br>"
            "Total Purchase: {total_purchase:,.2f} ETB<br>"
            "Total WHT Deducted: {total_wht:,.2f} ETB<br><br>"
            "This certificate is issued in compliance with "
            "Proclamation No. 979/2016 Art. 97."
        ).format(
            supplier_name=cert.supplier_name or cert.supplier,
            period_from=frappe.utils.format_date(cert.period_from),
            period_to=frappe.utils.format_date(cert.period_to),
            cert_name=cert.name,
            total_purchase=flt(cert.total_purchase_amount),
            total_wht=flt(cert.total_wht_deducted)
        )

        frappe.sendmail(
            recipients=[contact_email],
            subject=subject,
            message=message,
            attachments=[{
                "fname": f"WHT_Certificate_{cert.name}.pdf",
                "fcontent": pdf_content
            }],
            reference_doctype="WHT Certificate",
            reference_name=cert.name
        )

    except Exception as e:
        frappe.log_error(
            f"Failed to email WHT Certificate {cert.name}: {e}",
            title="WHT Certificate Email Error"
        )
        frappe.msgprint(
            _("WHT Certificate {0} was generated but email failed: {1}").format(
                cert.name, str(e)
            ),
            title=_("WHT Certificate — Email Error")
        )


def _get_supplier_contact_email(supplier):
    """Return the primary contact email for a supplier.

    Args:
        supplier (str): Supplier name

    Returns:
        str | None: Primary contact email, or fallback email if primary not set
    """
    email = frappe.db.get_value(
        "Contact",
        {"supplier": supplier, "is_primary_contact": 1},
        "email_id"
    )
    if not email:
        email = frappe.db.get_value(
            "Contact",
            {"supplier": supplier},
            "email_id"
        )
    return email


def count_pending_certificates():
    """Number card: count WHT Certificates in Draft status (not yet issued).

    Returns:
        int: count of pending WHT certificates
    """
    try:
        return frappe.db.count("WHT Certificate", {"docstatus": 0})
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Ethiopia Compliance Error: count_pending_certificates"
        )
        return 0