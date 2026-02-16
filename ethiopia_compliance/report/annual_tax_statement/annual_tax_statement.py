# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate

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
    data = []
    
    year = int(filters.get("year"))
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get Salary Slips with Component Details for the whole year
    entries = frappe.db.sql("""
        SELECT 
            ss.employee,
            ss.employee_name,
            emp.tax_id as tin_number,
            ss.gross_pay,
            ss.net_pay,
            sd.salary_component,
            sd.amount
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
        WHERE ss.company = %(company)s
        AND ss.start_date BETWEEN %(start_date)s AND %(end_date)s
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
                "tin_number": row.tin_number,
                "total_gross_pay": 0,
                "total_taxable_income": 0,
                "total_income_tax": 0,
                "total_pension": 0,
                "net_pay": 0
            }
            
        # For gross/net pay, we have duplication because of JOIN with Salary Detail
        # Logic issue: Joining with Salary Detail causes multiplication of rows for same slip
        # Better approach: Get slips first, then details, OR aggregation
    
    # Let's fix the logic
    # 1. Get Employee totals from Salary Slips (Gross, Net)
    # 2. Get Component totals from Details
    
    # A: Slips Aggregate
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
            "total_taxable_income": flt(row.total_gross), # Approximation
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
            if "Income Tax" in row.salary_component:
                final_data[row.employee]["total_income_tax"] += flt(row.total_amount)
            if "Pension (Employee)" in row.salary_component or "7%" in row.salary_component:
                final_data[row.employee]["total_pension"] += flt(row.total_amount)
    
    return list(final_data.values())
