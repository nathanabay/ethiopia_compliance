import frappe

def run():
    company = frappe.defaults.get_user_default("Company") or frappe.get_all("Company")[0].name
    print(f"--- Adding Missing Service Template for: {company} ---")

    # 1. SMART ACCOUNT FINDER
    # Try finding VAT account by exact name pattern first
    vat_account = frappe.db.get_value("Account", {"account_name": ["like", "Input VAT 15% -%"], "company": company}, "name")
    
    # Fallback 1: Search for any 'Tax' account with 'VAT' in the name
    if not vat_account:
        vat_account = frappe.db.get_value("Account", {"account_type": "Tax", "account_name": ["like", "%VAT%"], "company": company}, "name")
    
    # Fallback 2: Search for ANY Tax account (Last Resort)
    if not vat_account:
        vat_account = frappe.db.get_value("Account", {"account_type": "Tax", "company": company}, "name")
        print(f"⚠ Warning: Using generic tax account: {vat_account}")

    if not vat_account:
        print("❌ CRITICAL: No Tax/VAT Account found. Please create one in Chart of Accounts.")
        return

    # Find WHT Asset Account
    wht_asset = frappe.db.get_value("Account", {"account_name": "Withholding Tax Receivable", "company": company}, "name")
    if not wht_asset:
        # Try finding it with the suffix
        wht_asset = frappe.db.get_value("Account", {"account_name": ["like", "Withholding Tax Receivable -%"], "company": company}, "name")

    if not wht_asset:
        print("❌ CRITICAL: WHT Receivable Account missing. Re-run 'sales_taxes.py'.")
        return

    print(f"✔ Using Accounts: VAT='{vat_account}', WHT='{wht_asset}'")

    # 2. CREATE TEMPLATE
    template_name = "Ethiopia Sales - Services (WHT 3%)"
    if not frappe.db.exists("Sales Taxes and Charges Template", template_name):
        frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "title": template_name,
            "company": company,
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": vat_account,
                    "description": "VAT (15%)",
                    "rate": 15
                },
                {
                    "charge_type": "On Net Total",
                    "account_head": wht_asset,
                    "description": "Less: WHT (3%)",
                    "rate": -3
                }
            ]
        }).insert(ignore_permissions=True)
        print(f"✔ Success: Created '{template_name}'")
    else:
        print(f"ℹ Template '{template_name}' already exists.")

    frappe.db.commit()
