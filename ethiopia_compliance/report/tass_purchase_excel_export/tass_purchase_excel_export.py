# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "tin", "label": _("Supplier TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "name", "label": _("Supplier Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice Number"), "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": _("Invoice Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "total", "label": _("Total Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "p_type", "label": _("Purchase Type"), "fieldtype": "Data", "width": 120}
	]

	conditions = ["p.docstatus = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("p.company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("from_date"):
		conditions.append("p.posting_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("p.posting_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	data = frappe.db.sql("""
		SELECT
			p.custom_supplier_tin as tin,
			p.supplier_name as name,
			p.bill_no as inv_no,
			p.bill_date as date,
			p.grand_total as total,
			CASE WHEN svc.parent IS NOT NULL THEN 'Services' ELSE 'Goods' END as p_type
		FROM `tabPurchase Invoice` p
		LEFT JOIN (
			SELECT DISTINCT pii.parent
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabItem` i ON pii.item_code = i.name
			WHERE i.is_stock_item = 0
		) svc ON p.name = svc.parent
		WHERE {where}
		ORDER BY p.posting_date DESC
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
