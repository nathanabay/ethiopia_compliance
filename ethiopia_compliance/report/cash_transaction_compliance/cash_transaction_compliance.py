# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

def _get_cash_limit():
    """Fetch cash_limit from Compliance Setting; fallback to 50000."""
    try:
        settings = frappe.get_single("Compliance Setting")
        return flt(settings.cash_limit) or 50000
    except Exception:
        return 50000


def execute(filters=None):
	if filters is None:
		filters = {}

	cash_limit = _get_cash_limit()

	columns = [
		{"fieldname": "posting_date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "voucher_type", "label": _("Type"), "fieldtype": "Data", "width": 130},
		{"fieldname": "voucher_no", "label": _("Voucher No"), "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 180},
		{"fieldname": "party_type", "label": _("Party Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "party", "label": _("Party"), "fieldtype": "Dynamic Link", "options": "party_type", "width": 150},
		{"fieldname": "party_name", "label": _("Party Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "amount", "label": _("Amount (ETB)"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "excess", "label": _("Excess Over Limit"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "status", "label": _("Compliance"), "fieldtype": "Data", "width": 140}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

	# Query Payment Entries (Cash)
	payment_entries = frappe.db.sql("""
		SELECT
			pe.posting_date,
			'Payment Entry' as voucher_type,
			pe.name as voucher_no,
			pe.party_type,
			pe.party,
			pe.party_name,
			pe.paid_amount as amount
		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
			AND pe.company = %(company)s
			AND pe.mode_of_payment = 'Cash'
			AND pe.paid_amount > %(cash_limit)s
			AND pe.posting_date >= %(from_date)s
			AND pe.posting_date <= %(to_date)s
		ORDER BY pe.posting_date, pe.name
		LIMIT 10000
	""", {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"],
		"cash_limit": cash_limit
	}, as_dict=True)

	# Query Journal Entries (Cash)
	journal_entries = frappe.db.sql("""
		SELECT
			je.posting_date,
			'Journal Entry' as voucher_type,
			je.name as voucher_no,
			jea.party_type,
			jea.party,
			'' as party_name,
			jea.credit as amount
		FROM `tabJournal Entry` je
		JOIN `tabJournal Entry Account` jea ON jea.parent = je.name
		WHERE je.docstatus = 1
			AND je.company = %(company)s
			AND jea.account_type IN ('Cash', 'Bank')
			AND jea.credit > %(cash_limit)s
			AND je.posting_date >= %(from_date)s
			AND je.posting_date <= %(to_date)s
		ORDER BY je.posting_date, je.name
		LIMIT 10000
	""", {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"],
		"cash_limit": cash_limit
	}, as_dict=True)

	# Combine and annotate
	data = []
	for row in payment_entries + journal_entries:
		amount = flt(row.amount)
		excess = flt(amount - cash_limit)
		data.append({
			"posting_date": row.posting_date,
			"voucher_type": row.voucher_type,
			"voucher_no": row.voucher_no,
			"party_type": row.party_type or "",
			"party": row.party or "",
			"party_name": row.get("party_name", ""),
			"amount": amount,
			"excess": excess,
			"status": _("Non-Compliant")
		})

	data.sort(key=lambda r: r["posting_date"])
	return columns, data
