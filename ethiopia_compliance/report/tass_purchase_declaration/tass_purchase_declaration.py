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
			c.tax_id as purchaser_tin,
			p.custom_supplier_tin as seller_tin,
			p.bill_no as receipt_no,
			p.bill_date as receipt_date,
			'G' as calendar_type,
			p.grand_total as amount,
			CASE
				WHEN goods.parent IS NOT NULL AND svc.parent IS NOT NULL THEN 'Mixed'
				WHEN svc.parent IS NOT NULL THEN 'Services'
				ELSE 'Goods'
			END as purchase_type
		FROM `tabPurchase Invoice` p
		JOIN `tabCompany` c ON p.company = c.name
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
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
