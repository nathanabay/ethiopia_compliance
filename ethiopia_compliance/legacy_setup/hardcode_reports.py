import frappe
import json

def run():
    print("--- 🧱 HARDCODING 'BESPO' INTO REPORTS (STATIC MODE) ---")
    
    # 1. TASS Sales (No variables, just raw SQL with BESPO hardcoded)
    sales_sql = """
    SELECT
        c.tax_id as "Seller TIN",
        cust.tax_id as "Buyer TIN",
        s.customer_name as "Buyer Name",
        s.custom_fiscal_machine_no as "MRC",
        s.custom_fs_number as "FS No",
        s.posting_date as "Date",
        s.grand_total as "Amount",
        CASE WHEN s.docstatus = 0 THEN 'Draft' ELSE 'Submitted' END as "Status"
    FROM
        `tabSales Invoice` s
        JOIN `tabCompany` c ON s.company = c.name
        LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
    WHERE
        s.docstatus < 2
        AND s.company = 'BESPO'  -- <--- HARDCODED
        AND s.posting_date >= '2025-01-01' -- <--- HARDCODED
    ORDER BY s.posting_date DESC
    """

    # 2. TASS Purchase
    purchase_sql = """
    SELECT
        c.tax_id as "Purchaser TIN",
        p.custom_supplier_tin as "Seller TIN",
        p.bill_no as "Receipt No",
        p.bill_date as "Date",
        p.grand_total as "Amount",
        'Goods' as "Type"
    FROM
        `tabPurchase Invoice` p
        JOIN `tabCompany` c ON p.company = c.name
    WHERE
        p.docstatus = 1
        AND p.company = 'BESPO' -- <--- HARDCODED
        AND p.posting_date >= '2025-01-01'
    """

    # 3. SIGTAS Withholding
    wht_sql = """
    SELECT
        p.custom_supplier_tin as "Supplier TIN",
        p.supplier_name as "Supplier Name",
        p.bill_no as "Invoice No",
        p.bill_date as "Date",
        p.total as "Taxable Amount",
        ABS(t.tax_amount) as "Tax Withheld"
    FROM
        `tabPurchase Taxes and Charges` t
        JOIN `tabPurchase Invoice` p ON t.parent = p.name
    WHERE
        p.docstatus = 1
        AND t.account_head LIKE '%Withholding%'
        AND p.company = 'BESPO' -- <--- HARDCODED
        AND p.posting_date >= '2025-01-01'
    """

    reports = {
        "TASS Sales Declaration": {"ref": "Sales Invoice", "sql": sales_sql},
        "TASS Purchase Declaration": {"ref": "Purchase Invoice", "sql": purchase_sql},
        "SIGTAS Withholding Report": {"ref": "Purchase Invoice", "sql": wht_sql}
    }

    # Clean filters (empty) so browser doesn't try to send anything
    empty_filters = "[]"

    for name, config in reports.items():
        if frappe.db.exists("Report", name):
            frappe.delete_doc("Report", name, force=1)
        
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": name,
            "ref_doctype": config["ref"],
            "report_type": "Query Report",
            "is_standard": "No",
            "module": "Ethiopia Compliance",
            "query": config["sql"],
            "json": empty_filters, # No filters = No crashes
            "disabled": 0
        })
        
        doc.insert(ignore_permissions=True)
        print(f"✔ Hardcoded Report: {name}")

    frappe.db.commit()
    frappe.clear_cache()
    print("--- ✅ DONE ---")
