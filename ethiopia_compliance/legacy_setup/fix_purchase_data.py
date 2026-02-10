import frappe

def run():
    print("--- 🔧 FIXING MISSING TIN DATA ---")
    
    # 1. Update Supplier with a TIN
    supplier_name = "Test Supplier - Ethiopia"
    if frappe.db.exists("Supplier", supplier_name):
        frappe.db.set_value("Supplier", supplier_name, "tax_id", "0012345678")
        print(f"✔ Added TIN '0012345678' to Supplier: {supplier_name}")
    
    # 2. Update the Purchase Invoice to reflect this TIN
    invoices = frappe.db.get_all("Purchase Invoice", filters={"supplier": supplier_name}, pluck="name")
    
    for inv_name in invoices:
        # Force update the custom TIN field on the invoice
        frappe.db.set_value("Purchase Invoice", inv_name, "custom_supplier_tin", "0012345678")
        print(f"✔ Updated Invoice {inv_name} with TIN")

    frappe.db.commit()
    
    # 3. VERIFY REPORT QUERY
    print("\n--- 🕵️ TESTING REPORT QUERY ---")
    
    # Test TASS Purchase Query
    sql = """
        SELECT name, custom_supplier_tin, grand_total 
        FROM `tabPurchase Invoice` 
        WHERE docstatus = 1
    """
    data = frappe.db.sql(sql, as_dict=True)
    print(f"📊 Found {len(data)} Purchase Invoices in Database:")
    for row in data:
        print(f"   - {row.name}: TIN={row.custom_supplier_tin}, Amount={row.grand_total}")

    print("\n--- ✅ DONE ---")
    print("👉 Go to browser > TASS Purchase Declaration")
    print("👉 Set Date Range: 2026-01-01 to 2026-12-31")
    print("👉 Click Refresh")

