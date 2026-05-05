# POESSA Pension Report
# Per-employee breakdown of pension contributions (7% employee + 11% employer = 18% total)
# Required by Ethiopian pension regulation for monthly POESSA filings

import frappe
from frappe import _
from frappe.utils import flt, formatdate
from calendar import monthrange

# Match common component naming conventions
BASIC_COMPONENTS = {"Basic Salary", "Basic"}
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}
ORG_PENSION_COMPONENTS = {"Pension (Employer)", "Employer Pension", "Employer Pension (11%)"}


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	report_summary = get_report_summary(data)
	return columns, data, None, None, report_summary


def get_columns():
	return [
		{
			"fieldname": "employee",
			"label": _("Employee"),
			"fieldtype": "Link",
			"options": "Employee",
			"width": 100
		},
		{
			"fieldname": "employee_name",
			"label": _("Employee Name"),
			"fieldtype": "Data",
			"width": 180
		},
		{
			"fieldname": "pension_number",
			"label": _("Pension No."),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "basic_salary",
			"label": _("Basic Salary"),
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"fieldname": "emp_pension",
			"label": _("Emp. Deduction (7%)"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "org_pension",
			"label": _("Employer Contr. (11%)"),
			"fieldtype": "Currency",
			"width": 150
		},
		{
			"fieldname": "total_pension",
			"label": _("Total Remittance (18%)"),
			"fieldtype": "Currency",
			"width": 160
		},
		{
			"fieldname": "salary_slip",
			"label": _("Salary Slip"),
			"fieldtype": "Link",
			"options": "Salary Slip",
			"width": 150
		}
	]


def get_data(filters):
	month_name = filters.get("month")
	if not month_name:
		frappe.throw(_("Month filter is required."))
	if not filters.get("year") or not filters.get("company"):
		frappe.throw(_("Company and Year filters are required."))

	month_map = {
		"January": 1, "February": 2, "March": 3, "April": 4,
		"May": 5, "June": 6, "July": 7, "August": 8,
		"September": 9, "October": 10, "November": 11, "December": 12
	}
	if month_name not in month_map:
		frappe.throw(_("Invalid month: {0}").format(month_name))

	month_idx = month_map[month_name]
	year = int(filters.get("year"))
	company = filters.get("company")

	_, last_day = monthrange(year, month_idx)
	start_date = f"{year}-{month_idx:02d}-01"
	end_date = f"{year}-{month_idx:02d}-{last_day:02d}"

	# Fetch all salary slips with their salary detail and employee pension numbers
	entries = frappe.db.sql("""
		SELECT
			ss.name as salary_slip,
			ss.employee,
			ss.employee_name,
			emp.custom_pension_number as pension_number,
			sd.salary_component,
			sd.amount
		FROM `tabSalary Slip` ss
		JOIN `tabSalary Detail` sd ON sd.parent = ss.name
		LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
		WHERE ss.company = %(company)s
			AND ss.start_date >= %(start_date)s
			AND ss.start_date <= %(end_date)s
			AND ss.docstatus = 1
		ORDER BY ss.employee, ss.name
		LIMIT 10000
	""", {
		"company": company,
		"start_date": start_date,
		"end_date": end_date
	}, as_dict=True)

	# Aggregate by employee + salary slip
	emp_data = {}
	for row in entries:
		key = row.salary_slip
		if key not in emp_data:
			emp_data[key] = {
				"salary_slip": row.salary_slip,
				"employee": row.employee,
				"employee_name": row.employee_name,
				"pension_number": row.pension_number or "",
				"basic_salary": 0.0,
				"emp_pension": 0.0,
				"org_pension": 0.0
			}

		if row.salary_component in BASIC_COMPONENTS:
			emp_data[key]["basic_salary"] += flt(row.amount)
		elif row.salary_component in EMP_PENSION_COMPONENTS:
			emp_data[key]["emp_pension"] += flt(row.amount)
		elif row.salary_component in ORG_PENSION_COMPONENTS:
			emp_data[key]["org_pension"] += flt(row.amount)

	# Calculate totals
	result = []
	for vals in emp_data.values():
		vals["basic_salary"] = flt(vals["basic_salary"], 2)
		vals["emp_pension"] = flt(vals["emp_pension"], 2)
		vals["org_pension"] = flt(vals["org_pension"], 2)
		vals["total_pension"] = flt(vals["emp_pension"] + vals["org_pension"], 2)
		result.append(vals)

	result.sort(key=lambda x: x["employee_name"])
	return result


def get_report_summary(data):
	if not data:
		return None

	total_basic = flt(sum(d["basic_salary"] for d in data), 2)
	total_emp = flt(sum(d["emp_pension"] for d in data), 2)
	total_org = flt(sum(d["org_pension"] for d in data), 2)
	total_all = flt(total_emp + total_org, 2)
	employee_count = len(set(d["employee"] for d in data))

	return [
		{"label": _("Employees"), "value": employee_count, "datatype": "Int"},
		{"label": _("Total Basic Salary"), "value": total_basic, "datatype": "Currency"},
		{"label": _("Total Emp. Deduction (7%)"), "value": total_emp, "datatype": "Currency"},
		{"label": _("Total Employer Contr. (11%)"), "value": total_org, "datatype": "Currency"},
		{"label": _("POESSA Remittance Due (18%)"), "value": total_all, "datatype": "Currency",
		 "indicator": "Red" if total_all > 0 else "Green"}
	]
