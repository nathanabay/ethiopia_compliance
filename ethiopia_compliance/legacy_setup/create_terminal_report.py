import frappe
import json

def run():
    print("--- 🖥️ CREATING DIRECT SQL REPORT ---")
    
    report_name = "Direct SQL Check"
    
    # 1. Delete if exists
    if frappe.db.exists("Report", report_name):
        frappe.delete_doc("Report", report_name, force=1)
        print(f"🗑 Deleted old version of {report_name}")

    # 2. Define the SQL Query (Hard-coded to show everything)
    sql_query = """
SELECT
    name as "Invoice ID",
    posting_date as "Date",
    company as "Company Name",
    grand_total as "Amount",
    status as "Status"
FROM
    `tabSales Invoice`
ORDER BY
    posting_date DESC
LIMIT 50
    """

    # 3. Create the Report Document
    doc = frappe.get_doc({
        "doctype": "Report",
        "report_name": report_name,
        "ref_doctype": "Sales Invoice",
        "report_type": "Query Report", # Pure SQL
        "is_standard": "No",           # Stored in Database (Custom)
        "module": "Ethiopia Compliance",
        "query": sql_query,            # Inject the SQL above
        "json": "[]",                  # NO FILTERS (Prevents filter crashes)
        "disabled": 0
    })
    
    doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    frappe.clear_cache()
    
    print(f"✔ Created Report: '{report_name}'")
    print("👉 Go to ERPNext > Search for 'Direct SQL Check'")
    print("--- ✅ DONE ---")
