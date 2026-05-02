# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

BASIC_COMPONENTS = {"Basic Salary", "Basic"}
ORG_PENSION_COMPONENTS = {"Pension (Employer)", "Employer Pension", "Employer Pension (11%)"}
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
            "fieldname": "org_pension",
            "label": _("Org. Pension (11%)"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "emp_pension",
            "label": _("Emp. Pension (7%)"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "gross_pay",
            "label": _("Gross Pay"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_pension",
            "label": _("Total Pension"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    # Calculate start and end date based on month/year
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
    
    from calendar import monthrange
    _, last_day = monthrange(year, month_idx)
    start_date = f"{year}-{month_idx:02d}-01"
    end_date = f"{year}-{month_idx:02d}-{last_day:02d}"

    # Single parameterized query to fetch slips with their components
    entries = frappe.db.sql("""
        SELECT
            ss.employee,
            ss.employee_name,
            ss.gross_pay,
            emp.custom_pension_number,
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

    # Process data
    emp_map = {}

    for row in entries:
        emp = row.employee
        if emp not in emp_map:
            emp_map[emp] = {
                "employee": row.employee,
                "employee_name": row.employee_name,
                "pension_number": row.custom_pension_number,
                "gross_pay": flt(row.gross_pay),
                "basic_salary": 0,
                "org_pension": 0,
                "emp_pension": 0
            }
        
        # Classify component by exact match
        if row.salary_component in BASIC_COMPONENTS:
            emp_map[emp]["basic_salary"] += flt(row.amount)
        elif row.salary_component in ORG_PENSION_COMPONENTS:
            emp_map[emp]["org_pension"] += flt(row.amount)
        elif row.salary_component in EMP_PENSION_COMPONENTS:
            emp_map[emp]["emp_pension"] += flt(row.amount)
    
    for emp, vals in emp_map.items():
        vals["gross_pay"] = flt(vals.get("gross_pay", 0))
        vals["total_pension"] = vals["org_pension"] + vals["emp_pension"]

    return list(emp_map.values())
