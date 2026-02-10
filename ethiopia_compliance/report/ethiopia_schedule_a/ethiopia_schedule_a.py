
import frappe

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
    
    conditions = "docstatus = 1"
    if filters.get("company"): conditions += f" AND company = '{filters.get('company')}'"
    
    if filters.get("from_date"): conditions += f" AND start_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND end_date <= '{filters.get('to_date')}'"

    # Fetch Salary Slips
    slips = frappe.db.sql(f"""
        SELECT 
            name,
            employee_name as emp_name,
            employee as emp_id,
            gross_pay,
            net_pay
        FROM `tabSalary Slip`
        WHERE {conditions}
    """, as_dict=1)
    
    data = []
    
    for slip in slips:
        # 1. Get Employee Details (TIN)
        emp_details = frappe.db.get_value("Employee", slip.emp_id, ["tax_id"], as_dict=1)
        emp_tin = emp_details.tax_id if emp_details else ""
        
        # 2. Get Earnings & Deductions Components
        components = frappe.db.sql(f"""
            SELECT salary_component, amount, type 
            FROM `tabSalary Detail` 
            WHERE parent = '{slip.name}'
        """, as_dict=1)
        
        basic = 0
        transport = 0
        overtime = 0
        other = 0
        tax = 0
        cost_share = 0
        
        for c in components:
            if c.salary_component == "Basic Salary" or c.salary_component == "Basic":
                basic += c.amount
            elif "Transport" in c.salary_component:
                transport += c.amount 
            elif "Overtime" in c.salary_component:
                overtime += c.amount
            elif c.salary_component == "Income Tax" or c.salary_component == "PAYE":
                tax += c.amount
            elif "Cost Sharing" in c.salary_component:
                cost_share += c.amount
            elif c.type == "Earning" and c.amount > 0:
                other += c.amount 
        
        # Adjust 'Other' to not double count
        other = other - basic - transport - overtime
        if other < 0: other = 0

        # Total Taxable (Proxy via Gross Pay for simplicity)
        total_taxable = slip.gross_pay 

        row = {
            "emp_tin": emp_tin,
            "emp_name": slip.emp_name,
            "basic_salary": basic,
            "transport_taxable": transport,
            "overtime": overtime,
            "other_taxable": other,
            "total_taxable": total_taxable,
            "tax_withheld": tax,
            "cost_sharing": cost_share,
            "net_pay": slip.net_pay
        }
        data.append(row)
    
    return columns, data
