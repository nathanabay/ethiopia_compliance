import frappe
import json
from frappe.utils import today

def run():
    print("--- 📊 CREATING TASS EXCEL EXPORT FORMAT ---")
    
    report_name = "TASS Purchase Excel Export"
    
    # 1. Delete if exists to ensure clean slate
    if frappe.db.exists("Report", report_name):
        frappe.delete_doc("Report", report_name, force=1)

    # 2. Define SQL with Exact Excel Headers
    # CHANGE THE TEXT INSIDE QUOTES "..." TO MATCH YOUR EXCEL FILE HEADERS
    sql_query = """
    SELECT
        p.custom_supplier_tin as "Supplier TIN",
        p.supplier_name as "Supplier Name",
        p.bill_no as "Invoice Number",
        DATE_FORMAT(p.bill_date, '%%d/%%m/%%Y') as "Invoice Date", -- DD/MM/YYYY Format
        p.grand_total as "Total Amount",
        CASE 
            WHEN EXISTS(SELECT 1 FROM `tabPurchase Invoice Item` pii 
                        LEFT JOIN `tabItem` i ON pii.item_code = i.name 
                        WHERE pii.parent = p.name AND i.is_stock_item = 0) 
            THEN 'Services' 
            ELSE 'Goods' 
        END as "Purchase Type"
    FROM
        `tabPurchase Invoice` p
    WHERE
        p.docstatus = 1
        AND p.company = 'BESPO' -- Ensures only your company data
    ORDER BY
        p.bill_date DESC
    """

    # 3. Create the Report
    doc = frappe.get_doc({
        "doctype": "Report",
        "report_name": report_name,
        "ref_doctype": "Purchase Invoice",
        "report_type": "Query Report",
        "is_standard": "No",
        "module": "Ethiopia Compliance",
        "query": sql_query,
        "json": "[]", # No filters to prevent crashes during export
        "disabled": 0
    })
    
    doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    frappe.clear_cache()
    
    print(f"✔ Created Report: '{report_name}'")
    print("👉 Go to ERPNext > Search for 'TASS Purchase Excel Export'")
    print("👉 Click 'Actions' > 'Export' > 'Excel'")
    print("--- ✅ DONE ---")
