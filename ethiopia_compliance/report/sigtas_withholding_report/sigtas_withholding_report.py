
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
    
    conditions = "1=1"
    if filters.get("company"): conditions += f" AND p.company = '{filters.get('company')}'"
    if filters.get("from_date"): conditions += f" AND p.posting_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"): conditions += f" AND p.posting_date <= '{filters.get('to_date')}'"

    # Logic: Find Taxes in Purchase Invoices where Account matches WHT
    data = frappe.db.sql(f"""
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
    """, as_dict=1)
    
    return columns, data
