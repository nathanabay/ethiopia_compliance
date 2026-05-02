# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ethiopia_compliance.utils import get_gc_date, get_tin_status

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "seller_tin", "label": _("Seller TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_tin", "label": _("Buyer TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_tin_status", "label": _("Buyer TIN Status"), "fieldtype": "Data", "width": 120},
		{"fieldname": "buyer_name", "label": _("Buyer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice No"), "fieldtype": "Data", "width": 160},
		{"fieldname": "doctype", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "mrc", "label": _("MRC (Machine Code)"), "fieldtype": "Data", "width": 140},
		{"fieldname": "fs_no", "label": _("Receipt No (FS)"), "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "net_total", "label": _("Net Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "tax_amount", "label": _("Tax Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "amount", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120}
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

	conditions = ["s.docstatus = 1"]
	values = {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"]
	}

	conditions.append("s.company = %(company)s")
	conditions.append("s.posting_date >= %(from_date)s")
	conditions.append("s.posting_date <= %(to_date)s")

	data = frappe.db.sql("""
		SELECT
			c.tax_id as seller_tin,
			cust.tax_id as buyer_tin,
			s.customer_name as buyer_name,
			s.name as inv_no,
			s.doctype as doctype,
			s.custom_fiscal_machine_no as mrc,
			s.custom_fs_number as fs_no,
			s.posting_date as date,
			s.net_total as net_total,
			s.total_taxes_and_charges as tax_amount,
			s.grand_total as amount
		FROM `tabSales Invoice` s
		JOIN `tabCompany` c ON s.company = c.name
		LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
		WHERE {where}
		ORDER BY s.posting_date, s.name
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	for row in data:
		row["buyer_tin_status"] = get_tin_status(row.get("buyer_tin"))

	return columns, data
