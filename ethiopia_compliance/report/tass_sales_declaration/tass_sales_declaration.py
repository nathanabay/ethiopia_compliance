
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
    
    conditions = "1=1"
    if filters.get("company"): conditions += f" AND s.company = '{filters.get('company')}'"
    if filters.get("from_date"): conditions += f" AND s.posting_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND s.posting_date <= '{filters.get('to_date')}'"

    data = frappe.db.sql(f"""
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
    """, as_dict=1)
    
    return columns, data
