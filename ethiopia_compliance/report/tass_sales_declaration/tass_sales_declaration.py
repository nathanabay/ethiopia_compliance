# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "seller_tin", "label": _("Seller TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_tin", "label": _("Buyer TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_name", "label": _("Buyer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice No"), "fieldtype": "Dynamic Link", "options": "doctype", "width": 160},
		{"fieldname": "doctype", "label": _("Type"), "fieldtype": "Data", "width": 100},
		{"fieldname": "mrc", "label": _("MRC (Machine Code)"), "fieldtype": "Data", "width": 140},
		{"fieldname": "fs_no", "label": _("Receipt No (FS)"), "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "net_total", "label": _("Net Total"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "tax_amount", "label": _("Tax Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "amount", "label": _("Grand Total"), "fieldtype": "Currency", "width": 120}
	]

	conditions = ["s.docstatus = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("s.company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("from_date"):
		conditions.append("s.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("s.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

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

	return columns, data
