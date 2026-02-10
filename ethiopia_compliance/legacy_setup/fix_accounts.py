import frappe

def run():
    # 1. Get the correct Company
    company = frappe.defaults.get_user_default("Company")
    if not company:
        company = frappe.get_all("Company")[0].name
    
    print(f"--- Setting up Accounts for: {company} ---")

    # 2. Define Accounts (Same as before)
    accounts_to_create = [
        ("Input VAT 15%", "Duties and Taxes", "Tax", "Asset"),
        ("TOT Expense", "Direct Expenses", "Chargeable", "Expense"),
        ("Withholding Tax", "Duties and Taxes", "Tax", "Asset"),
        ("Customs Duty", "Direct Expenses", "Chargeable", "Expense"),
        ("Sur Tax", "Direct Expenses", "Chargeable", "Expense"),
        ("Excise Tax", "Direct Expenses", "Chargeable", "Expense")
    ]
    
    account_map = {}

    for name, parent_partial, acc_type, root_type in accounts_to_create:
        # A. Find Parent
        parent = frappe.db.get_value("Account", 
            {"account_name": ["like", f"%{parent_partial}%"], "company": company, "is_group": 1})
        
        if not parent:
            parent = frappe.db.get_value("Account", 
                {"account_type": root_type, "company": company, "is_group": 1, "is_root": 0})
            if not parent:
                 print(f"Skipping {name} (No parent found).")
                 continue

        # B. Check/Create
        existing = frappe.db.get_value("Account", {"account_name": ["like", f"{name}%"], "company": company})
        
        if existing:
            account_map[name] = existing
            print(f"✔ Found existing: {existing}")
        else:
            try:
                new_acc = frappe.get_doc({
                    "doctype": "Account",
                    "account_name": name,
                    "company": company,
                    "parent_account": parent,
                    "account_type": acc_type,
                    "currency": "ETB", 
                    "report_type": "Balance Sheet" if root_type == "Asset" else "Profit and Loss"
                })
                new_acc.insert(ignore_permissions=True)
                account_map[name] = new_acc.name
                print(f"✔ Created: {new_acc.name}")
            except Exception as e:
                print(f"Error creating {name}: {e}")

    # 3. Create Tax Templates
    create_local_vat(company, account_map)
    create_local_tot(company, account_map)
    create_import_duties(company, account_map)
    
    frappe.db.commit()
    print("--- SUCCESS: Accounts and Templates Configured ---")

def create_local_vat(company, am):
    name = "Ethiopia Local VAT 15%"
    if "Input VAT 15%" in am and not frappe.db.exists("Purchase Taxes and Charges Template", name):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": name,
            "company": company,
            "taxes": [
                {"charge_type": "On Net Total", "account_head": am["Input VAT 15%"], "description": "VAT 15% (Recoverable)", "rate": 15}
            ]
        }).insert(ignore_permissions=True)
        print("✔ Created Template: Local VAT 15%")

def create_local_tot(company, am):
    name = "Ethiopia Local TOT 2%"
    if "TOT Expense" in am and not frappe.db.exists("Purchase Taxes and Charges Template", name):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": name,
            "company": company,
            "taxes": [
                {"charge_type": "On Net Total", "account_head": am["TOT Expense"], "description": "TOT 2%", "rate": 2, "category": "Valuation and Total", "add_deduct_tax": "Add"}
            ]
        }).insert(ignore_permissions=True)
        print("✔ Created Template: Local TOT 2%")

def create_import_duties(company, am):
    name = "Ethiopia Import Duties"
    required = ["Customs Duty", "Excise Tax", "Sur Tax", "Input VAT 15%", "Withholding Tax"]
    
    if all(k in am for k in required) and not frappe.db.exists("Purchase Taxes and Charges Template", name):
         # We define the reference_row_id explicitly relative to the item list index
         frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": name,
            "company": company,
            "taxes": [
                # Row 1
                {"charge_type": "Actual", "account_head": am["Customs Duty"], "description": "Customs Duty", "rate": 0, "idx": 1},
                # Row 2
                {"charge_type": "Actual", "account_head": am["Excise Tax"], "description": "Excise Tax", "rate": 0, "idx": 2},
                # Row 3 (Sur Tax 10% on Subtotal of Row 1 & 2) -> "On Previous Row Total" usually requires referencing the specific row idx
                # FIX: Changing to "On Previous Row Amount" references the immediate predecessor, or "On Previous Row Total" references the cumulative.
                # To be safe for generic install, we set it to 'On Previous Row Total' and let ERPNext handle the cumulative.
                {"charge_type": "On Previous Row Total", "account_head": am["Sur Tax"], "description": "Sur Tax (10%)", "rate": 10, "idx": 3, "row_id": "2"}, 
                
                # Row 4 (VAT 15% on everything so far)
                {"charge_type": "On Previous Row Total", "account_head": am["Input VAT 15%"], "description": "VAT (15%)", "rate": 15, "idx": 4, "row_id": "3"},
                
                # Row 5 (WHT on Net Total)
                {"charge_type": "On Net Total", "account_head": am["Withholding Tax"], "description": "WHT (3%)", "rate": 3, "idx": 5}
            ]
        }).insert(ignore_permissions=True)
         print("✔ Created Template: Import Duties")
