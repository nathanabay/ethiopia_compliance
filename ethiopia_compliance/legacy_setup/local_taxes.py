import frappe

def create_local_templates():
    # 1. Create Accounts if missing
    ensure_account("Input VAT 15% - B", "Asset", "Tax")
    ensure_account("TOT Expense - B", "Expense", "Chargeable")
    
    # 2. Template A: VAT 15% (Recoverable)
    if not frappe.db.exists("Purchase Taxes and Charges Template", "Ethiopia Local VAT 15%"):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": "Ethiopia Local VAT 15%",
            "company": frappe.defaults.get_user_default("Company"),
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "Input VAT 15% - B",
                    "description": "VAT 15% (Recoverable)",
                    "rate": 15
                }
                # WHT is handled by your script, so we exclude it here to avoid double-entry errors
            ]
        }).insert(ignore_permissions=True)

    # 3. Template B: TOT 2% (Cost of Goods)
    if not frappe.db.exists("Purchase Taxes and Charges Template", "Ethiopia Local TOT 2%"):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": "Ethiopia Local TOT 2%",
            "company": frappe.defaults.get_user_default("Company"),
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": "TOT Expense - B",
                    "description": "Turnover Tax (Non-Recoverable)",
                    "rate": 2,
                    "add_deduct_tax": "Add",
                    "category": "Valuation and Total" # Adds to Item Cost
                }
            ]
        }).insert(ignore_permissions=True)
    
    print("Created Local Tax Templates: VAT 15% and TOT 2%")

def ensure_account(name, report_type, account_type):
    # Simplified account creator
    pass 
