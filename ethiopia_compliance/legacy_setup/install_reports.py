import frappe
import os

def run():
    print("--- Installing Ethiopian Regulatory Reports ---")
    base_path = frappe.get_app_path("ethiopia_compliance", "report")
    
    # 1. Install TASS Purchase Report
    create_report_files(base_path, "TASS Purchase Declaration", purchase_logic(), purchase_js())
    register_report("TASS Purchase Declaration", "Purchase Invoice", "Ethiopia Compliance")
    
    # 2. Install TASS Sales Report
    create_report_files(base_path, "TASS Sales Declaration", sales_logic(), sales_js())
    register_report("TASS Sales Declaration", "Sales Invoice", "Ethiopia Compliance")
    
    # 3. Install SIGTAS WHT Report
    create_report_files(base_path, "SIGTAS Withholding Report", wht_logic(), wht_js())
    register_report("SIGTAS Withholding Report", "Purchase Invoice", "Ethiopia Compliance")
    
    frappe.db.commit()
    print("✔ Reports Installed. Run 'bench restart' to activate.")

def create_report_files(base_path, report_name, py_content, js_content):
    # Create folder (slugified)
    slug = report_name.lower().replace(" ", "_")
    report_dir = os.path.join(base_path, slug)
    if not os.path.exists(report_dir):
        os.makedirs(report_dir)
    
    # Write .py file
    with open(os.path.join(report_dir, f"{slug}.py"), "w") as f:
        f.write(py_content)
    
    # Write .js file
    with open(os.path.join(report_dir, f"{slug}.js"), "w") as f:
        f.write(js_content)
        
    # Write .json file (skeleton)
    with open(os.path.join(report_dir, f"{slug}.json"), "w") as f:
        f.write("{}")

def register_report(name, ref_doctype, module):
    if not frappe.db.exists("Report", name):
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": name,
            "ref_doctype": ref_doctype,
            "report_type": "Script Report",
            "module": module,
            "is_standard": "No" # We treat as custom to avoid file permission issues
        })
        doc.insert(ignore_permissions=True)
        print(f"✔ Registered Report: {name}")

# --- REPORT LOGIC GENERATORS ---

def purchase_logic():
    return """
import frappe

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

    # Fetch Data
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

def purchase_js():
    return """
frappe.query_reports["TASS Purchase Declaration"] = {
    "filters": [
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "default": frappe.datetime.get_today()}
    ]
};
"""

def sales_logic():
    return """
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_tin", "label": "Buyer TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_name", "label": "Buyer Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "mrc", "label": "MRC (Machine Code)", "fieldtype": "Data", "width": 140},
        {"fieldname": "fs_no", "label": "Receipt No (FS)", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "amount", "label": "Total Amount", "fieldtype": "Currency", "width": 120}
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
            s.grand_total as amount
        FROM `tabSales Invoice` s
        JOIN `tabCompany` c ON s.company = c.name
        LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
        WHERE s.docstatus = 1 {conditions}
    \"\"\", as_dict=1)
    
    return columns, data
"""

def sales_js():
    return """
frappe.query_reports["TASS Sales Declaration"] = {
    "filters": [
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "default": frappe.datetime.get_today()}
    ]
};
"""

def wht_logic():
    return """
import frappe

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

    # Logic: Find Taxes in Purchase Invoices where Account matches WHT
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

def wht_js():
    return """
frappe.query_reports["SIGTAS Withholding Report"] = {
    "filters": [
        {"fieldname": "from_date", "label": "From Date", "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)},
        {"fieldname": "to_date", "label": "To Date", "fieldtype": "Date", "default": frappe.datetime.get_today()}
    ]
};
"""
