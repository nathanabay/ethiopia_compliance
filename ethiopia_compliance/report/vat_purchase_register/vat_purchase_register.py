# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ethiopia_compliance.utils import get_gc_date

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "purchaser_tin", "label": _("Purchaser TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "seller_tin", "label": _("Seller TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "seller_name", "label": _("Seller Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice No"), "fieldtype": "Data", "width": 160},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "taxable_amount", "label": _("Taxable Amount"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "vat_rate", "label": _("VAT Rate"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "vat_amount", "label": _("VAT Amount"), "fieldtype": "Currency", "width": 130}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

	# Ethiopian Calendar date conversion
	if filters.get("use_ethiopian_calendar"):
		if filters.get("from_date"):
			parts = str(filters["from_date"]).split("-")
			if len(parts) == 3:
				eth_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
				gc_date = get_gc_date(eth_date)
				if gc_date:
					filters["from_date"] = gc_date
		if filters.get("to_date"):
			parts = str(filters["to_date"]).split("-")
			if len(parts) == 3:
				eth_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
				gc_date = get_gc_date(eth_date)
				if gc_date:
					filters["to_date"] = gc_date

	conditions = ["p.docstatus = 1"]
	values = {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"],
		"vat_account": "%%VAT%%"
	}

	conditions.append("p.company = %(company)s")
	conditions.append("p.posting_date >= %(from_date)s")
	conditions.append("p.posting_date <= %(to_date)s")

	data = frappe.db.sql("""
		SELECT
			c.tax_id as purchaser_tin,
			p.custom_supplier_tin as seller_tin,
			p.supplier_name as seller_name,
			p.bill_no as inv_no,
			p.bill_date as date,
			p.net_total as taxable_amount,
			tc.rate as vat_rate,
			tc.tax_amount as vat_amount
		FROM `tabPurchase Invoice` p
		JOIN `tabPurchase Taxes and Charges` tc ON tc.parent = p.name
		JOIN `tabCompany` c ON p.company = c.name
		WHERE tc.account_head LIKE %(vat_account)s
			AND {where}
		ORDER BY p.posting_date, p.name
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
