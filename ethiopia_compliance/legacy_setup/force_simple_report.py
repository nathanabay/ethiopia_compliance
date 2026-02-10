import frappe

def run():
    print("--- 🔨 CREATING 'ZERO-LOGIC' SIMPLE REPORT ---")
    
    # 1. Delete the "Smart" Report
    if frappe.db.exists("Report", "TASS Sales Declaration"):
        frappe.delete_doc("Report", "TASS Sales Declaration", force=1)
        print("🗑 Deleted old complex report")

    # 2. Create the "Dumb" Report (Pure SQL, No Variables)
    # Note: We do NOT use %(from_date)s here. We just select everything.
    simple_sql = """
    SELECT
        name as "Invoice ID",
        posting_date as "Date",
        customer as "Customer",
        grand_total as "Amount",
        docstatus as "DocStatus (1=Sub)"
    FROM
        `tabSales Invoice`
    ORDER BY
        posting_date DESC
    LIMIT 50
    """

    doc = frappe.get_doc({
        "doctype": "Report",
        "report_name": "TASS Sales Declaration",
        "ref_doctype": "Sales Invoice",
        "report_type": "Query Report", # Pure SQL
        "is_standard": "No",
        "module": "Ethiopia Compliance",
        "query": simple_sql, # The simple query above
        "disabled": 0,
        # We explicitly set filters to None so it doesn't look for them
        "json": "[]" 
    })
    
    doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    frappe.clear_cache()
    
    print("✔ Created Simple SQL Report. It should show the last 50 invoices.")
    print("--- ✅ DONE ---")
