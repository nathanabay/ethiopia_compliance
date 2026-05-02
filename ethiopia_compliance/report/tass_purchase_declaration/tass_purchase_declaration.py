# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "purchaser_tin", "label": _("Purchaser TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "seller_tin", "label": _("Seller TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "receipt_no", "label": _("Receipt No"), "fieldtype": "Data", "width": 120},
		{"fieldname": "receipt_date", "label": _("Receipt Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "calendar_type", "label": _("Calendar (G/E)"), "fieldtype": "Data", "width": 100},
		{"fieldname": "amount", "label": _("Amount"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "purchase_type", "label": _("Type (Goods/Services)"), "fieldtype": "Data", "width": 150}
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
			c.tax_id as purchaser_tin,
			p.custom_supplier_tin as seller_tin,
			p.bill_no as receipt_no,
			p.bill_date as receipt_date,
			'G' as calendar_type,
			p.grand_total as amount,
			CASE WHEN svc.parent IS NOT NULL THEN 'Services' ELSE 'Goods' END as purchase_type
		FROM `tabPurchase Invoice` p
		JOIN `tabCompany` c ON p.company = c.name
		LEFT JOIN (
			SELECT DISTINCT pii.parent
			FROM `tabPurchase Invoice Item` pii
			JOIN `tabItem` i ON pii.item_code = i.name
			WHERE i.is_stock_item = 0
		) svc ON p.name = svc.parent
		WHERE {where}
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
