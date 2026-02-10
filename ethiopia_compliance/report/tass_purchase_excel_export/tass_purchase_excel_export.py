
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "tin", "label": "Supplier TIN", "fieldtype": "Data", "width": 140},
        {"fieldname": "name", "label": "Supplier Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "inv_no", "label": "Invoice Number", "fieldtype": "Data", "width": 120},
        {"fieldname": "date", "label": "Invoice Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "total", "label": "Total Amount", "fieldtype": "Currency", "width": 120},
        {"fieldname": "p_type", "label": "Purchase Type", "fieldtype": "Data", "width": 120}
    ]
    
    conditions = "1=1"
    if filters.get("company"): 
        conditions += f" AND p.company = '{filters.get('company')}'"
    if filters.get("from_date"):
        conditions += f" AND p.bill_date >= '{filters.get('from_date')}'"
    if filters.get("to_date"):
        conditions += f" AND p.bill_date <= '{filters.get('to_date')}'"

    # SQL adapted from fixtures/report.json
    data = frappe.db.sql(f"""
        SELECT
            p.custom_supplier_tin as tin,
            p.supplier_name as name,
            p.bill_no as inv_no,
            p.bill_date as date, 
            p.grand_total as total,
            CASE 
                WHEN EXISTS(SELECT 1 FROM `tabPurchase Invoice Item` pii 
                            LEFT JOIN `tabItem` i ON pii.item_code = i.name 
                            WHERE pii.parent = p.name AND i.is_stock_item = 0) 
                THEN 'Services' 
                ELSE 'Goods' 
            END as p_type
        FROM
            `tabPurchase Invoice` p
        WHERE
            p.docstatus = 1
            AND {conditions}
        ORDER BY
            p.bill_date DESC
    """, as_dict=1)
    
    return columns, data
