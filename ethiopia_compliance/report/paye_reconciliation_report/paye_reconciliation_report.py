# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from collections import defaultdict
from frappe.utils import flt
from ethiopia_compliance.utils import compute_paye_tax

INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}

MONTH_MAP = {
	"January": "01", "February": "02", "March": "03", "April": "04",
	"May": "05", "June": "06", "July": "07", "August": "08",
	"September": "09", "October": "10", "November": "11", "December": "12"
}


def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "employee", "label": _("Employee"), "fieldtype": "Link", "options": "Employee", "width": 100},
		{"fieldname": "employee_name", "label": _("Employee Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "salary_slip", "label": _("Salary Slip"), "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		{"fieldname": "gross_pay", "label": _("Gross Pay"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "emp_pension", "label": _("Emp. Pension (7%)"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "taxable_income", "label": _("Taxable Income"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "expected_paye", "label": _("Expected PAYE"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "actual_paye", "label": _("Actual PAYE Withheld"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "difference", "label": _("Difference"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "status", "label": _("Status"), "fieldtype": "Data", "width": 130}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("month"):
		frappe.throw(_("Month filter is required."))
	if not filters.get("year"):
		frappe.throw(_("Year filter is required."))
	if filters["month"] not in MONTH_MAP:
		frappe.throw(_("Invalid month."))

	from datetime import date, timedelta
	import calendar

	month_num = int(MONTH_MAP[filters["month"]])
	year = int(filters["year"])

	last_day = calendar.monthrange(year, month_num)[1]
	start_date = date(year, month_num, 1)
	end_date = date(year, month_num, last_day)

	# Get salary slips
	slips = frappe.db.sql("""
		SELECT name, employee, employee_name, gross_pay
		FROM `tabSalary Slip`
		WHERE docstatus = 1
			AND company = %(company)s
			AND start_date >= %(start_date)s
			AND end_date <= %(end_date)s
		ORDER BY employee
	""", {
		"company": filters["company"],
		"start_date": start_date,
		"end_date": end_date
	}, as_dict=True)

	if not slips:
		return columns, []

	# Batch fetch salary components
	slip_names = [s.name for s in slips]
	if not slip_names:
		return columns, []

	all_components = frappe.db.sql("""
		SELECT parent, salary_component, amount
		FROM `tabSalary Detail`
		WHERE parent IN %(slip_names)s
	""", {"slip_names": slip_names}, as_dict=True)

	# Build per-slip component map
	slip_map = {}
	for s in slips:
		slip_map[s.name] = {
			"employee": s.employee,
			"employee_name": s.employee_name,
			"salary_slip": s.name,
			"gross_pay": flt(s.gross_pay),
			"emp_pension": 0.0,
			"actual_paye": 0.0
		}

	for c in all_components:
		if c.parent in slip_map:
			if c.salary_component in EMP_PENSION_COMPONENTS:
				slip_map[c.parent]["emp_pension"] += flt(c.amount)
			elif c.salary_component in INCOME_TAX_COMPONENTS:
				slip_map[c.parent]["actual_paye"] += flt(c.amount)

	# Compute expected PAYE and flag discrepancies
	data = []
	tolerance = 1.0  # ETB 1 tolerance for rounding differences

	for slip_name, vals in slip_map.items():
		taxable_income = vals["gross_pay"] - vals["emp_pension"]
		expected_paye = compute_paye_tax(taxable_income)
		actual_paye = vals["actual_paye"]
		difference = flt(actual_paye - expected_paye, 2)

		if abs(difference) <= tolerance:
			status = _("Correct")
		elif difference > 0:
			status = _("Over-withheld")
		else:
			status = _("Under-withheld")

		data.append({
			"employee": vals["employee"],
			"employee_name": vals["employee_name"],
			"salary_slip": vals["salary_slip"],
			"gross_pay": vals["gross_pay"],
			"emp_pension": vals["emp_pension"],
			"taxable_income": flt(taxable_income, 2),
			"expected_paye": expected_paye,
			"actual_paye": actual_paye,
			"difference": difference,
			"status": status
		})

	return columns, data
