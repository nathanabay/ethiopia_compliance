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

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

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
			p.grand_total as total,
			CASE
				WHEN goods.parent IS NOT NULL AND svc.parent IS NOT NULL THEN 'Mixed'
				WHEN svc.parent IS NOT NULL THEN 'Services'
				ELSE 'Goods'
			END as p_type
		FROM `tabPurchase Invoice` p
		LEFT JOIN (
			SELECT DISTINCT pii.parent
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabItem` i ON pii.item_code = i.name
			WHERE i.is_stock_item = 1
		) goods ON p.name = goods.parent
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
