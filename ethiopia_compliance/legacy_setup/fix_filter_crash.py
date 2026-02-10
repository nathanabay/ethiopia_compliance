import frappe
from frappe.utils import today

def run():
    print("--- 🛡️ APPLYING ANTI-CRASH FILTER LOGIC ---")
    
    # 1. TASS Sales Declaration (Safe Python Wrapper)
    sales_code = """
def execute(filters=None):
    # SAFETY BLOCK: Handle empty filters
    if not filters: filters = {}
    if not filters.get("from_date"): filters["from_date"] = "2024-01-01"
    if not filters.get("to_date"): filters["to_date"] = frappe.utils.today()

    columns = [
        {"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_tin", "label": "Buyer TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "buyer_name", "label": "Buyer Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "mrc", "label": "MRC", "fieldtype": "Data", "width": 140},
        {"fieldname": "fs_no", "label": "FS No", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 80}
    ]
    
    # Safe SQL execution
    sql = \"\"\"
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
        WHERE s.docstatus < 2 
        AND s.posting_date >= %(from_date)s 
        AND s.posting_date <= %(to_date)s
    \"\"\"
    
    data = frappe.db.sql(sql, filters, as_dict=1)
    return columns, data
"""

    # 2. TASS Purchase Declaration (Safe Python Wrapper)
    purchase_code = """
def execute(filters=None):
    if not filters: filters = {}
    if not filters.get("from_date"): filters["from_date"] = "2024-01-01"
    if not filters.get("to_date"): filters["to_date"] = frappe.utils.today()

    columns = [
        {"fieldname": "purchaser_tin", "label": "Purchaser TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "seller_tin", "label": "Seller TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "receipt_no", "label": "Receipt No", "fieldtype": "Data", "width": 120},
        {"fieldname": "receipt_date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "type", "label": "Type", "fieldtype": "Data", "width": 100}
    ]
    
    sql = \"\"\"
        SELECT 
            c.tax_id as purchaser_tin, 
            p.custom_supplier_tin as seller_tin, 
            p.bill_no as receipt_no, 
            p.bill_date as receipt_date, 
            p.grand_total as amount, 
            'Goods' as type 
        FROM `tabPurchase Invoice` p 
        JOIN `tabCompany` c ON p.company = c.name 
        WHERE p.docstatus = 1 
        AND p.posting_date >= %(from_date)s 
        AND p.posting_date <= %(to_date)s
    \"\"\"

    data = frappe.db.sql(sql, filters, as_dict=1)
    return columns, data
"""

    # 3. SIGTAS Withholding (Safe Python Wrapper)
    wht_code = """
def execute(filters=None):
    if not filters: filters = {}
    if not filters.get("from_date"): filters["from_date"] = "2024-01-01"
    if not filters.get("to_date"): filters["to_date"] = frappe.utils.today()

    columns = [
        {"fieldname": "tin", "label": "TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "name", "label": "Supplier", "fieldtype": "Data", "width": 180},
        {"fieldname": "inv_no", "label": "Inv No", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "taxable", "label": "Taxable", "fieldtype": "Currency", "width": 120},
        {"fieldname": "wht", "label": "WHT Amount", "fieldtype": "Currency", "width": 120}
    ]
    
    sql = \"\"\"
        SELECT 
            p.custom_supplier_tin as tin, 
            p.supplier_name as name, 
            p.bill_no as inv_no, 
            p.bill_date as date, 
            p.total as taxable, 
            ABS(t.tax_amount) as wht 
        FROM `tabPurchase Taxes and Charges` t 
        JOIN `tabPurchase Invoice` p ON t.parent = p.name 
        WHERE p.docstatus = 1 
        AND t.account_head LIKE '%%Withholding%%' 
        AND p.posting_date >= %(from_date)s 
        AND p.posting_date <= %(to_date)s
    \"\"\"

    data = frappe.db.sql(sql, filters, as_dict=1)
    return columns, data
"""

    reports = {
        "TASS Sales Declaration": sales_code,
        "TASS Purchase Declaration": purchase_code,
        "SIGTAS Withholding Report": wht_code
    }

    for name, code in reports.items():
        if frappe.db.exists("Report", name):
            # 1. Convert back to Script Report (Python)
            frappe.db.set_value("Report", name, "report_type", "Script Report")
            frappe.db.set_value("Report", name, "is_standard", "No")
            frappe.db.set_value("Report", name, "query", "") # Clear SQL field
            
            # 2. Inject Safe Python Code
            frappe.db.set_value("Report", name, "report_script", code)
            
            # 3. Disable Background Execution
            if frappe.db.has_column("Report", "prepared_report"):
                frappe.db.set_value("Report", name, "prepared_report", 0)
                
            print(f"✔ Fixed & Secured: {name}")

    frappe.db.commit()
    frappe.clear_cache()
    print("--- ✅ DONE ---")
