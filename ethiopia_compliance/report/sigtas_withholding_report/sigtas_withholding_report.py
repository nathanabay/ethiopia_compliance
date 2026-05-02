# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ethiopia_compliance.utils import get_gc_date, get_tin_status

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "tin", "label": _("Supplier TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "tin_status", "label": _("TIN Status"), "fieldtype": "Data", "width": 110},
		{"fieldname": "name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice No"), "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "taxable", "label": _("Taxable Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "rate", "label": _("Rate"), "fieldtype": "Percent", "width": 80},
		{"fieldname": "wht_amount", "label": _("Tax Withheld"), "fieldtype": "Currency", "width": 120}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

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
		"to_date": filters["to_date"]
	}

	conditions.append("p.company = %(company)s")
	conditions.append("p.posting_date >= %(from_date)s")
	conditions.append("p.posting_date <= %(to_date)s")

	data = frappe.db.sql("""
		SELECT
			p.custom_supplier_tin as tin,
			p.supplier_name as name,
			p.bill_no as inv_no,
			p.bill_date as date,
			p.base_total as taxable,
			t.rate as rate,
			ABS(t.tax_amount) as wht_amount
		FROM `tabPurchase Taxes and Charges` t
		JOIN `tabPurchase Invoice` p ON t.parent = p.name
		WHERE t.account_head LIKE %(wht_account)s
			AND {where}
	""".format(where=" AND ".join(conditions)), {
		**values,
		"wht_account": "%%Withholding%%"
	}, as_dict=True)

	for row in data:
		row["tin_status"] = get_tin_status(row.get("tin"))

	return columns, data
