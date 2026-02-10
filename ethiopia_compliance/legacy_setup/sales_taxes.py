import frappe

def run():
    # 1. Get Company
    company = frappe.defaults.get_user_default("Company")
    if not company:
        companies = frappe.get_all("Company")
        if companies:
            company = companies[0].name
        else:
            print("❌ No Company found.")
            return

    print(f"--- Configuring Sales Taxes for: {company} ---")

    # 2. Find/Create 'Withholding Tax Receivable' (Asset)
    # This acts as an Asset because the customer keeps this money to pay the gov on your behalf.
    wht_account_name = "Withholding Tax Receivable"
    wht_account = frappe.db.get_value("Account", {"account_name": wht_account_name, "company": company}, "name")

    if not wht_account:
        # Find a suitable parent (Tax Assets or Current Assets)
        parent = frappe.db.get_value("Account", 
            {"account_name": ["like", "%Tax Assets%"], "company": company, "is_group": 1}, "name")
        if not parent:
            parent = frappe.db.get_value("Account", 
                {"account_name": ["like", "%Current Assets%"], "company": company, "is_group": 1}, "name")
        
        if parent:
            doc = frappe.get_doc({
                "doctype": "Account",
                "account_name": wht_account_name,
                "parent_account": parent,
                "company": company,
                "account_type": "Tax", 
                "report_type": "Balance Sheet",
                "currency": "ETB"
            })
            doc.insert(ignore_permissions=True)
            wht_account = doc.name
            print(f"✔ Created Account: {wht_account}")
        else:
            print("❌ Could not find parent account for Assets.")
            return
    else:
        print(f"✔ Found Account: {wht_account}")

    # 3. Find VAT Account (Output VAT)
    # Usually 'Output VAT 15%' or similar
    vat_account = frappe.db.get_value("Account", {"account_name": ["like", "%Output VAT%"], "company": company}, "name")
    if not vat_account:
        vat_account = frappe.db.get_value("Account", {"account_name": ["like", "%VAT%"], "company": company}, "name")
    
    if not vat_account:
        print("⚠ Output VAT Account not found. Skipping Template creation.")
        return

    # 4. Create Template: "Ethiopia Sales - Goods (VAT 15% + WHT 2%)"
    template_name = "Ethiopia Sales - Goods (VAT 15% + WHT 2%)"
    if not frappe.db.exists("Sales Taxes and Charges Template", template_name):
        doc = frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "title": template_name,
            "company": company,
            "is_default": 1,
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": vat_account,
                    "description": "VAT 15%",
                    "rate": 15
                },
                {
                    # WHT is deducted from what the customer pays you
                    "charge_type": "On Net Total",
                    "account_head": wht_account,
                    "description": "Withholding Tax (Receivable)",
                    "rate": -2 
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print(f"✔ Created Template: {template_name}")
    else:
        print(f"✔ Template already exists: {template_name}")

    frappe.db.commit()
