
import frappe

def execute(filters=None):
	columns = [
		{"fieldname": "tin", "label": "Supplier TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "name", "label": "Supplier Name", "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": "Invoice No", "fieldtype": "Data", "width": 120},
		{"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
		{"fieldname": "taxable", "label": "Taxable Amount", "fieldtype": "Currency", "width": 120},
		{"fieldname": "rate", "label": "Rate", "fieldtype": "Percent", "width": 80},
		{"fieldname": "wht_amount", "label": "Tax Withheld", "fieldtype": "Currency", "width": 120}
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
			p.total as taxable,
			'3%' as rate,
			ABS(t.tax_amount) as wht_amount
		FROM `tabPurchase Taxes and Charges` t
		JOIN `tabPurchase Invoice` p ON t.parent = p.name
		WHERE t.account_head LIKE '%%Withholding%%'
			AND {where}
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
