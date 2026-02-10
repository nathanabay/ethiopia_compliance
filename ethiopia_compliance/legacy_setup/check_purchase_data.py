import frappe

def run():
    print("--- 🕵️ CHECKING PURCHASE DATA FOR 'BESPO' ---")
    
    # 1. Search for ANY Purchase Invoice for BESPO
    pi_list = frappe.db.sql("""
        SELECT name, posting_date, grand_total, docstatus, company 
        FROM `tabPurchase Invoice` 
        WHERE company = 'BESPO'
    """, as_dict=True)
    
    if not pi_list:
        print("❌ CRITICAL: No Purchase Invoices found for 'BESPO'.")
        print("   (This explains why the report is empty!)")
        create_purchase_invoice()
    else:
        print(f"✅ Found {len(pi_list)} Purchase Invoices for BESPO:")
        for pi in pi_list:
            status = "Submitted" if pi.docstatus == 1 else "Draft" if pi.docstatus == 0 else "Cancelled"
            print(f"   - {pi.name} | {pi.posting_date} | {pi.grand_total} | {status}")

def create_purchase_invoice():
    print("\n--- 🛠 CREATING TEST PURCHASE INVOICE FOR 'BESPO' ---")
    try:
        # Create Supplier if missing
        supp = "Test Supplier - BESPO"
        if not frappe.db.exists("Supplier", supp):
            frappe.get_doc({"doctype": "Supplier", "supplier_name": supp, "supplier_group": "Local", "tax_id": "0012345678"}).insert()

        # Create Item if missing
        item = "Consulting Service"
        if not frappe.db.exists("Item", item):
            frappe.get_doc({"doctype": "Item", "item_code": item, "item_group": "Services", "is_stock_item": 0}).insert()

        # Create Invoice
        pi = frappe.get_doc({
            "doctype": "Purchase Invoice",
            "supplier": supp,
            "company": "BESPO",  # <--- FORCE CORRECT COMPANY
            "posting_date": frappe.utils.today(),
            "bill_no": "TEST-BILL-001",
            "bill_date": frappe.utils.today(),
            "items": [{"item_code": item, "qty": 1, "rate": 50000}]
        })
        
        pi.insert()
        pi.submit()
        
        frappe.db.commit()
        print(f"✅ Created & Submitted Purchase Invoice: {pi.name}")
        
    except Exception as e:
        print(f"❌ Failed to create invoice: {e}")

