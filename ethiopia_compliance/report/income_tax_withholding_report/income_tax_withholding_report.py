# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

BASIC_COMPONENTS = {"Basic Salary", "Basic"}
INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
COST_SHARING_COMPONENTS = {"Cost Sharing", "Cost Sharing (Employee)"}
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "tin_number",
            "label": _("TIN Number"),
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
            "fieldname": "taxable_income",
            "label": _("Taxable Income"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "income_tax",
            "label": _("Income Tax"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "cost_sharing",
            "label": _("Cost Sharing"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_pay",
            "label": _("Net Pay"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4,
        "May": 5, "June": 6, "July": 7, "August": 8,
        "September": 9, "October": 10, "November": 11, "December": 12
    }

    month_name = filters.get("month")
    if not month_name or month_name not in month_map:
        frappe.throw(_("A valid Month is required."))
    if not filters.get("year") or not filters.get("company"):
        frappe.throw(_("Company and Year are required filters."))

    month_idx = month_map[month_name]
    year = int(filters.get("year"))
    
    # Calculate date range from month/year to avoid MONTH()/YEAR() in WHERE
    from calendar import monthrange
    _, last_day = monthrange(year, month_idx)
    start_date = f"{year}-{month_idx:02d}-01"
    end_date = f"{year}-{month_idx:02d}-{last_day:02d}"

    # Get Salary Slips with Component Details in a single batched query
    entries = frappe.db.sql("""
        SELECT
            ss.employee,
            ss.employee_name,
            emp.tax_id as tin_number,
            ss.net_pay,
            ss.gross_pay,
            sd.salary_component,
            sd.amount
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
        WHERE ss.company = %(company)s
        AND ss.start_date >= %(start_date)s
        AND ss.start_date <= %(end_date)s
        AND ss.docstatus = 1
    """, {
        "company": filters.get("company"),
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)

    # Process data in a single pass — no N+1 queries
    emp_map = {}

    for row in entries:
        emp = row.employee
        if emp not in emp_map:
            emp_map[emp] = {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "tin_number": row.tin_number,
                "basic_salary": 0,
                "gross_pay": flt(row.gross_pay),
                "taxable_income": 0,
                "income_tax": 0,
                "cost_sharing": 0,
                "emp_pension": 0,
                "net_pay": flt(row.net_pay)
            }

        # Categorize components by exact match
        if row.salary_component in BASIC_COMPONENTS:
            emp_map[emp]["basic_salary"] += flt(row.amount)
        elif row.salary_component in INCOME_TAX_COMPONENTS:
            emp_map[emp]["income_tax"] += flt(row.amount)
        elif row.salary_component in COST_SHARING_COMPONENTS:
            emp_map[emp]["cost_sharing"] += flt(row.amount)
        elif row.salary_component in EMP_PENSION_COMPONENTS:
            emp_map[emp]["emp_pension"] += flt(row.amount)

    # Compute taxable income: gross pay minus employee pension (7%)
    for emp_data in emp_map.values():
        emp_data["taxable_income"] = emp_data["gross_pay"] - emp_data["emp_pension"]

    data = list(emp_map.values())
    return data
