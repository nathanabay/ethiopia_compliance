import frappe
import json
from frappe.utils import today

def run():
    print("--- 🚀 APPLYING FINAL WORKING SQL TO ALL REPORTS ---")
    
    # 1. TASS Sales Declaration (Using the logic that worked)
    # We use COALESCE to handle filters safely in SQL
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
        AND s.company = %(company)s
        AND s.posting_date >= %(from_date)s
        AND s.posting_date <= %(to_date)s
    ORDER BY s.posting_date DESC
    """

    # 2. TASS Purchase Declaration
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
        AND p.company = %(company)s
        AND p.posting_date >= %(from_date)s
        AND p.posting_date <= %(to_date)s
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
        AND t.account_head LIKE '%%Withholding%%'
        AND p.company = %(company)s
        AND p.posting_date >= %(from_date)s
        AND p.posting_date <= %(to_date)s
    """

    reports = {
        "TASS Sales Declaration": {"ref": "Sales Invoice", "sql": sales_sql},
        "TASS Purchase Declaration": {"ref": "Purchase Invoice", "sql": purchase_sql},
        "SIGTAS Withholding Report": {"ref": "Purchase Invoice", "sql": wht_sql}
    }

    # Standard Filters Configuration
    filters_json = json.dumps([
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "default": "BESPO", # <--- FORCE DEFAULT TO YOUR COMPANY
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": "2026-01-01",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": today(),
            "reqd": 1
        }
    ])

    for name, config in reports.items():
        # Clean slate
        if frappe.db.exists("Report", name):
            frappe.delete_doc("Report", name, force=1)
        
        # Create Report
        doc = frappe.get_doc({
            "doctype": "Report",
            "report_name": name,
            "ref_doctype": config["ref"],
            "report_type": "Query Report", # PURE SQL = NO CRASH
            "is_standard": "No",
            "module": "Ethiopia Compliance",
            "query": config["sql"],
            "json": filters_json,
            "disabled": 0
        })
        
        doc.insert(ignore_permissions=True)
        print(f"✔ Fixed & Restored: {name}")

    frappe.db.commit()
    frappe.clear_cache()
    print("--- ✅ DONE ---")
