import frappe

def run():
    print("--- 🔧 UPDATING REPORT TO SHOW DRAFTS ---")
    
    # 1. Update Sales Report SQL to allow docstatus 0 (Draft) and 1 (Submitted)
    sales_code = """
import frappe

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
    
    # Update Database
    frappe.db.sql("UPDATE `tabReport` SET report_script = %s WHERE name = 'TASS Sales Declaration'", (sales_code,))
    
    frappe.db.commit()
    print("✔ TASS Sales Declaration now shows Draft invoices!")
    frappe.clear_cache()
