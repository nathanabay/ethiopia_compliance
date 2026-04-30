
import frappe
from collections import defaultdict


def execute(filters=None):
	columns = [
		{"fieldname": "emp_tin", "label": "Employee TIN", "fieldtype": "Data", "width": 140},
		{"fieldname": "emp_name", "label": "Employee Name", "fieldtype": "Data", "width": 200},
		{"fieldname": "basic_salary", "label": "Basic Salary", "fieldtype": "Currency", "width": 120},
		{"fieldname": "transport_taxable", "label": "Taxable Transport", "fieldtype": "Currency", "width": 120},
		{"fieldname": "overtime", "label": "Overtime", "fieldtype": "Currency", "width": 100},
		{"fieldname": "other_taxable", "label": "Other Taxable", "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_taxable", "label": "Total Taxable Income", "fieldtype": "Currency", "width": 140},
		{"fieldname": "tax_withheld", "label": "Tax Withheld (PAYE)", "fieldtype": "Currency", "width": 140},
		{"fieldname": "cost_sharing", "label": "Cost Sharing", "fieldtype": "Currency", "width": 100},
		{"fieldname": "net_pay", "label": "Net Pay", "fieldtype": "Currency", "width": 120}
	]

	conditions = ["docstatus = 1"]
	values = {}

	if filters.get("company"):
		conditions.append("company = %(company)s")
		values["company"] = filters["company"]
	if filters.get("from_date"):
		conditions.append("start_date >= %(from_date)s")
		values["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		conditions.append("end_date <= %(to_date)s")
		values["to_date"] = filters["to_date"]

	# Single query for salary slips
	slips = frappe.db.sql("""
		SELECT
			name,
			employee_name as emp_name,
			employee as emp_id,
			gross_pay,
			net_pay
		FROM `tabSalary Slip`
		WHERE {where}
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	if not slips:
		return columns, []

	# Batch fetch employee TINs (1 query instead of N)
	emp_ids = list({s.emp_id for s in slips})
	emp_tins = {}
	for emp_name, tax_id in frappe.db.get_values("Employee", emp_ids, ["name", "tax_id"]):
		emp_tins[emp_name] = tax_id or ""

	# Batch fetch salary components (1 query instead of N)
	slip_names = [s.name for s in slips]
	all_components = frappe.db.sql("""
		SELECT parent, salary_component, amount, type
		FROM `tabSalary Detail`
		WHERE parent IN %(slip_names)s
	""", {"slip_names": slip_names}, as_dict=True)

	components_by_parent = defaultdict(list)
	for c in all_components:
		components_by_parent[c.parent].append(c)

	# Build data from batched results
	data = []
	for slip in slips:
		components = components_by_parent.get(slip.name, [])
		emp_tin = emp_tins.get(slip.emp_id, "")

		basic = 0
		transport = 0
		overtime = 0
		other = 0
		tax = 0
		cost_share = 0

		for c in components:
			if c.salary_component in ("Basic Salary", "Basic"):
				basic += c.amount
			elif "Transport" in c.salary_component:
				transport += c.amount
			elif "Overtime" in c.salary_component:
				overtime += c.amount
			elif c.salary_component in ("Income Tax", "PAYE"):
				tax += c.amount
			elif "Cost Sharing" in c.salary_component:
				cost_share += c.amount
			elif c.type == "Earning" and c.amount > 0:
				other += c.amount

		other = other - basic - transport - overtime
		if other < 0:
			other = 0

		row = {
			"emp_tin": emp_tin,
			"emp_name": slip.emp_name,
			"basic_salary": basic,
			"transport_taxable": transport,
			"overtime": overtime,
			"other_taxable": other,
			"total_taxable": slip.gross_pay,
			"tax_withheld": tax,
			"cost_sharing": cost_share,
			"net_pay": slip.net_pay
		}
		data.append(row)

	return columns, data
