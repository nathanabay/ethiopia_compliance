
import frappe

def execute(filters=None):
	columns = [
		{"fieldname": "tin", "label": "Supplier TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "name", "label": "Supplier Name", "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": "Invoice Number", "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": "Invoice Date", "fieldtype": "Data", "width": 100},
		{"fieldname": "total", "label": "Total Amount", "fieldtype": "Currency", "width": 120},
		{"fieldname": "p_type", "label": "Purchase Type", "fieldtype": "Data", "width": 120}
	]

	conditions = ["p.docstatus = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("p.company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("from_date"):
		conditions.append("p.bill_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("p.bill_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	data = frappe.db.sql("""
		SELECT
			p.custom_supplier_tin as tin,
			p.supplier_name as name,
			p.bill_no as inv_no,
			p.bill_date as date,
			p.grand_total as total,
			CASE
				WHEN EXISTS(
					SELECT 1 FROM `tabPurchase Invoice Item` pii
					LEFT JOIN `tabItem` i ON pii.item_code = i.name
					WHERE pii.parent = p.name AND i.is_stock_item = 0
				) THEN 'Services'
				ELSE 'Goods'
			END as p_type
		FROM `tabPurchase Invoice` p
		WHERE {where}
		ORDER BY p.bill_date DESC
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
