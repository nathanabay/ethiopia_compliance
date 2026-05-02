# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict

BASIC_COMPONENTS = {"Basic Salary", "Basic"}
TRANSPORT_COMPONENTS = {"Transport Allowance", "Transport", "Transportation Allowance"}
OVERTIME_COMPONENTS = {"Overtime", "Overtime Pay"}
INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
COST_SHARING_COMPONENTS = {"Cost Sharing", "Cost Sharing (Employee)"}
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}


def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "emp_tin", "label": _("Employee TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "emp_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 200},
		{"fieldname": "basic_salary", "label": _("Basic Salary"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "transport_taxable", "label": _("Taxable Transport"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "overtime", "label": _("Overtime"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "other_taxable", "label": _("Other Taxable"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "total_taxable", "label": _("Total Taxable Income"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "tax_withheld", "label": _("Tax Withheld (PAYE)"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "cost_sharing", "label": _("Cost Sharing"), "fieldtype": "Currency", "width": 100},
		{"fieldname": "net_pay", "label": _("Net Pay"), "fieldtype": "Currency", "width": 120}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

	conditions = ["docstatus = 1"]
	values = {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"]
	}

	conditions.append("company = %(company)s")
	conditions.append("start_date >= %(from_date)s")
	conditions.append("end_date <= %(to_date)s")

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
		emp_pension = 0

		for c in components:
			if c.salary_component in BASIC_COMPONENTS:
				basic += c.amount
			elif c.salary_component in TRANSPORT_COMPONENTS:
				transport += c.amount
			elif c.salary_component in OVERTIME_COMPONENTS:
				overtime += c.amount
			elif c.salary_component in INCOME_TAX_COMPONENTS:
				tax += c.amount
			elif c.salary_component in COST_SHARING_COMPONENTS:
				cost_share += c.amount
			elif c.salary_component in EMP_PENSION_COMPONENTS:
				emp_pension += c.amount
			elif c.type == "Earning" and c.amount > 0:
				other += c.amount

		row = {
			"emp_tin": emp_tin,
			"emp_name": slip.emp_name,
			"basic_salary": basic,
			"transport_taxable": transport,
			"overtime": overtime,
			"other_taxable": other,
			"total_taxable": slip.gross_pay - emp_pension,
			"tax_withheld": tax,
			"cost_sharing": cost_share,
			"net_pay": slip.net_pay
		}
		data.append(row)

	return columns, data
