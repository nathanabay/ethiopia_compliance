import frappe

def run():
    print("--- 🧭 DATA LOCATOR ---")
    
    # 1. Find the invoices and their Company
    invoices = frappe.db.get_all("Sales Invoice", 
        fields=["name", "company", "owner", "docstatus"],
        filters={"docstatus": ["<", 2]},
        limit=5
    )
    
    if not invoices:
        print("❌ CRITICAL: No Invoices found in the database. Data is genuinely missing.")
    else:
        print(f"✅ Found {len(invoices)} Invoices. Details below:")
        for inv in invoices:
            status = "Submitted" if inv.docstatus == 1 else "Draft"
            print(f"   📄 Invoice: {inv.name}")
            print(f"      🏢 Company: {inv.company} <--- YOU MUST BE IN THIS COMPANY")
            print(f"      👤 Owner:   {inv.owner}")
            print(f"      🔒 Status:  {status}")
            print("---")

    # 2. Check User Permissions
    user = frappe.session.user
    print(f"👤 Current System User: {user}")
    
    roles = frappe.get_roles(user)
    print(f"🔑 Roles: {roles}")

    print("\n👉 ACTION: Go to ERPNext, click your Avatar > Switch Company/Session Defaults.")
    print("👉 Ensure you selected the 'Company' listed above.")
