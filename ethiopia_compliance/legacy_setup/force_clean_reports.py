import frappe

def run():
    print("--- 🧼 OVERWRITING REPORTS WITH SANITIZED CODE ---")

    # 1. TASS Sales Declaration (With Draft Support)
    tass_sales_code = """
def execute(filters=None):
    columns = [
        {"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_tin", "label": "Buyer TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_name", "label": "Buyer Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "mrc", "label": "MRC (Machine Code)", "fieldtype": "Data", "width": 140},
        {"fieldname": "fs_no", "label": "Receipt No (FS)", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "amount", "label": "Total Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 80}
    ]
    
    conditions = ""
    if filters.get("from_date"): conditions += f" AND posting_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND posting_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(f\"\"\"
        SELECT 
            c.tax_id as seller_tin,
            cust.tax_id as buyer_tin,
            s.customer_name as buyer_name,
            s.custom_fiscal_machine_no as mrc,
            s.custom_fs_number as fs_no,
            s.posting_date as date,
            s.grand_total as amount,
            CASE WHEN s.docstatus = 0 THEN 'Draft' ELSE 'Submitted' END as status
        FROM `tabSales Invoice` s
        JOIN `tabCompany` c ON s.company = c.name
        LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
        WHERE s.docstatus < 2 {conditions}
    \"\"\", as_dict=1)
    
    return columns, data
"""

    # 2. TASS Purchase Declaration
    tass_purchase_code = """
def execute(filters=None):
    columns = [
        {"fieldname": "purchaser_tin", "label": "Purchaser TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "receipt_no", "label": "Receipt No", "fieldtype": "Data", "width": 120},
        {"fieldname": "receipt_date", "label": "Receipt Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "calendar_type", "label": "Calendar (G/E)", "fieldtype": "Data", "width": 100},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "purchase_type", "label": "Type (Goods/Services)", "fieldtype": "Data", "width": 150}
    ]
    
    conditions = ""
    if filters.get("from_date"): conditions += f" AND posting_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND posting_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(f\"\"\"
        SELECT 
            c.tax_id as purchaser_tin,
            p.custom_supplier_tin as seller_tin,
            p.bill_no as receipt_no,
            p.bill_date as receipt_date,
            'G' as calendar_type,
            p.grand_total as amount,
            CASE 
                WHEN EXISTS(SELECT 1 FROM `tabPurchase Invoice Item` pii 
                            LEFT JOIN `tabItem` i ON pii.item_code = i.name 
                            WHERE pii.parent = p.name AND i.is_stock_item = 0) 
                THEN 'Services' 
                ELSE 'Goods' 
            END as purchase_type
        FROM `tabPurchase Invoice` p
        JOIN `tabCompany` c ON p.company = c.name
        WHERE p.docstatus = 1 {conditions}
    \"\"\", as_dict=1)
    
    return columns, data
"""

    # 3. SIGTAS Withholding Report
    sigtas_wht_code = """
def execute(filters=None):
    columns = [
        {"fieldname": "tin", "label": "Supplier TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "name", "label": "Supplier Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "inv_no", "label": "Invoice No", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "taxable", "label": "Taxable Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "rate", "label": "Rate", "fieldtype": "Percent", "width": 80},
        {"fieldname": "wht_amount", "label": "Tax Withheld", "fieldtype": "Currency", "width": 120}
    ]
    
    conditions = ""
    if filters.get("from_date"): conditions += f" AND p.posting_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND p.posting_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(f\"\"\"
        SELECT 
            p.custom_supplier_tin as tin,
            p.supplier_name as name,
            p.bill_no as inv_no,
            p.bill_date as date,
            p.total as taxable,
            '3%' as rate,
            ABS(t.tax_amount) as wht_amount
        FROM `tabPurchase Taxes and Charges` t
        JOIN `tabPurchase Invoice` p ON t.parent = p.name
        WHERE 
            p.docstatus = 1 
            AND t.account_head LIKE '%Withholding%'
            {conditions}
    \"\"\", as_dict=1)
    
    return columns, data
"""

    # 4. Ethiopia Schedule A
    schedule_a_code = """
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

    slips = frappe.db.sql(f\"\"\"
        SELECT 
            name,
            employee_name as emp_name,
            employee as emp_id,
            gross_pay,
            net_pay
        FROM `tabSalary Slip`
        WHERE {conditions}
    \"\"\", as_dict=1)
    
    data = []
    
    for slip in slips:
        emp_details = frappe.db.get_value("Employee", slip.emp_id, ["tax_id"], as_dict=1)
        emp_tin = emp_details.tax_id if emp_details else ""
        
        components = frappe.db.sql(f\"\"\"
            SELECT salary_component, amount, type 
            FROM `tabSalary Detail` 
            WHERE parent = '{slip.name}'
        \"\"\", as_dict=1)
        
        basic = 0
        transport = 0
        overtime = 0
        other = 0
        tax = 0
        cost_share = 0
        
        for c in components:
            if c.salary_component in ["Basic Salary", "Basic"]:
                basic += c.amount
            elif "Transport" in c.salary_component:
                transport += c.amount 
            elif "Overtime" in c.salary_component:
                overtime += c.amount
            elif c.salary_component in ["Income Tax", "PAYE"]:
                tax += c.amount
            elif "Cost Sharing" in c.salary_component:
                cost_share += c.amount
            elif c.type == "Earning" and c.amount > 0:
                other += c.amount 
        
        other = other - basic - transport - overtime
        if other < 0: other = 0

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
"""

    # Apply Updates
    reports = {
        "TASS Sales Declaration": tass_sales_code,
        "TASS Purchase Declaration": tass_purchase_code,
        "SIGTAS Withholding Report": sigtas_wht_code,
        "Ethiopia Schedule A": schedule_a_code
    }

    for report, code in reports.items():
        if frappe.db.exists("Report", report):
            frappe.db.sql("""
                UPDATE `tabReport`
                SET 
                    is_standard = 0,
                    report_type = 'Script Report',
                    report_script = %s,
                    disabled = 0
                WHERE name = %s
            """, (code, report))
            print(f"✔ FIXED: {report}")
        else:
            print(f"⚠ Missing: {report}")

    frappe.db.commit()
    print("--- 💾 Cache Cleared ---")
    frappe.clear_cache()
