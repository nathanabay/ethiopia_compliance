
import frappe

def execute(filters=None):
	columns = [
		{"fieldname": "purchaser_tin", "label": "Purchaser TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "receipt_no", "label": "Receipt No", "fieldtype": "Data", "width": 120},
		{"fieldname": "receipt_date", "label": "Receipt Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "calendar_type", "label": "Calendar (G/E)", "fieldtype": "Data", "width": 100},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
		{"fieldname": "purchase_type", "label": "Type (Goods/Services)", "fieldtype": "Data", "width": 150}
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
			CASE
				WHEN EXISTS(
					SELECT 1 FROM `tabPurchase Invoice Item` pii
					LEFT JOIN `tabItem` i ON pii.item_code = i.name
					WHERE pii.parent = p.name AND i.is_stock_item = 0
				) THEN 'Services'
				ELSE 'Goods'
			END as purchase_type
		FROM `tabPurchase Invoice` p
		JOIN `tabCompany` c ON p.company = c.name
		WHERE {where}
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
