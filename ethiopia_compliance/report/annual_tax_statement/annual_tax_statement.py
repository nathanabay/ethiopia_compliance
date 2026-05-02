# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}

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
            "fieldname": "total_gross_pay",
            "label": _("Total Gross Pay"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_taxable_income",
            "label": _("Total Taxable Income"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "total_income_tax",
            "label": _("Total Income Tax"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_pension",
            "label": _("Total Pension (7%)"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_pay",
            "label": _("Total Net Pay"),
            "fieldtype": "Currency",
            "width": 120
        }
    ]

def get_data(filters):
    if not filters.get("year") or not filters.get("company"):
        frappe.throw(_("Company and Year are required filters."))

    year = int(filters.get("year"))
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # A: Slips Aggregate — get totals from Salary Slips
    slips_agg = frappe.db.sql("""
        SELECT 
            ss.employee,
            ss.employee_name,
            emp.tax_id as tin_number,
            SUM(ss.gross_pay) as total_gross,
            SUM(ss.net_pay) as total_net
        FROM `tabSalary Slip` ss
        LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
        WHERE ss.company = %(company)s
        AND ss.start_date BETWEEN %(start_date)s AND %(end_date)s
        AND ss.docstatus = 1
        GROUP BY ss.employee
    """, {
        "company": filters.get("company"),
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)
    
    # Map for easy access
    final_data = {}
    for row in slips_agg:
        final_data[row.employee] = {
            "employee": row.employee,
            "employee_name": row.employee_name,
            "tin_number": row.tin_number,
            "total_gross_pay": flt(row.total_gross),
            "total_taxable_income": 0,
            "total_income_tax": 0,
            "total_pension": 0,
            "net_pay": flt(row.total_net)
        }
    
    # B: Components Aggregate
    components_agg = frappe.db.sql("""
        SELECT 
            ss.employee,
            sd.salary_component,
            SUM(sd.amount) as total_amount
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.company = %(company)s
        AND ss.start_date BETWEEN %(start_date)s AND %(end_date)s
        AND ss.docstatus = 1
        GROUP BY ss.employee, sd.salary_component
    """, {
        "company": filters.get("company"),
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)
    
    for row in components_agg:
        if row.employee in final_data:
            if row.salary_component in INCOME_TAX_COMPONENTS:
                final_data[row.employee]["total_income_tax"] += flt(row.total_amount)
            if row.salary_component in PENSION_COMPONENTS:
                final_data[row.employee]["total_pension"] += flt(row.total_amount)
    
    # Compute taxable income: gross pay minus employee pension (7%)
    for emp_data in final_data.values():
        emp_data["total_taxable_income"] = emp_data["total_gross_pay"] - emp_data["total_pension"]

    return list(final_data.values())
