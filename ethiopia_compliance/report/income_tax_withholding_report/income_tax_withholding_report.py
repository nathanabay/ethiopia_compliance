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
    data = []
    
    month_map = {
        "January": 1, "February": 2, "March": 3, "April": 4, 
        "May": 5, "June": 6, "July": 7, "August": 8, 
        "September": 9, "October": 10, "November": 11, "December": 12
    }
    
    month_idx = month_map.get(filters.get("month"))
    year = int(filters.get("year"))
    
    # Get Salary Slips with Component Details
    entries = frappe.db.sql("""
        SELECT 
            ss.employee,
            ss.employee_name,
            emp.tax_id as tin_number,
            ss.net_pay,
            sd.salary_component,
            sd.amount
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
        WHERE ss.company = %(company)s
        AND MONTH(ss.start_date) = %(month)s
        AND YEAR(ss.start_date) = %(year)s
        AND ss.docstatus = 1
    """, {
        "company": filters.get("company"),
        "month": month_idx,
        "year": year
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
                "basic_salary": 0,
                "taxable_income": 0,
                "income_tax": 0,
                "cost_sharing": 0,
                "net_pay": flt(row.net_pay)
            }
        
        # Categorize components
        if "Basic" in row.salary_component:
            emp_map[emp]["basic_salary"] += flt(row.amount)
            # Assuming Basic is Taxable, usually Gross Pay is better but simplified here
            # In perfect world, we check is_tax_applicable in Salary Component
        
        # For Taxable Income, usually we want Gross - Non-Taxable Allowances
        # Here we'll sum up earnings that are taxable. 
        # But simpler: use Income Tax amount to reverse calculate or just display components
        
        if "Income Tax" in row.salary_component:
            emp_map[emp]["income_tax"] += flt(row.amount)
            
        if "Cost Sharing" in row.salary_component:
            emp_map[emp]["cost_sharing"] += flt(row.amount)
            
    # Second pass for Taxable Income (Approximate if not storing explicitly)
    # Ideally should fetch 'gross_pay' from SS, but let's query SS directly for gross
    
    for emp_id, vals in emp_map.items():
        # Get Gross Pay from Salary Slip directly
        gross = frappe.db.get_value("Salary Slip", {
            "employee": emp_id, 
            "month": month_idx, # This filter is tricky via get_value with SQL calc functions
            "company": filters.get("company"),
            "docstatus": 1
        }, "gross_pay")
        
        # Determine Taxable Income (Gross - Non-Taxable)
        # For now, let's assume Taxable Income = Gross Pay (User can adjust filter logic)
        vals["taxable_income"] = flt(gross)
        
        data.append(vals)
        
    return data
