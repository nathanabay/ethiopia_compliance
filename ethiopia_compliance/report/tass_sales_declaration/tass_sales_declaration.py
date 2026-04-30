
import frappe

def execute(filters=None):
	columns = [
		{"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_tin", "label": "Buyer TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_name", "label": "Buyer Name", "fieldtype": "Data", "width": 180},
		{"fieldname": "mrc", "label": "MRC (Machine Code)", "fieldtype": "Data", "width": 140},
		{"fieldname": "fs_no", "label": "Receipt No (FS)", "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "amount", "label": "Total Amount", "fieldtype": "Currency", "width": 120}
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
			s.custom_fiscal_machine_no as mrc,
			s.custom_fs_number as fs_no,
			s.posting_date as date,
			s.grand_total as amount
		FROM `tabSales Invoice` s
		JOIN `tabCompany` c ON s.company = c.name
		LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
		WHERE {where}
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
