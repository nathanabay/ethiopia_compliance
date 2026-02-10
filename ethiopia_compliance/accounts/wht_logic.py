import frappe

def apply_withholding_tax(doc, method):
    """
    Applies 3% Withholding Tax (WHT) as per Proclamation 1395/2025.
    """
    # 1. Check if Supplier is WHT Eligible
    supplier_wht = frappe.db.get_value("Supplier", doc.supplier, "custom_wht_eligible")
    if not supplier_wht:
        return

    # 2. Determine Threshold based on Item Types
    current_threshold = 20000 # Default to Goods
    
    for item in doc.items:
        is_stock = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        if not is_stock:
            current_threshold = 10000 # Strict service threshold
            break 

    # 3. Apply Tax if Grand Total exceeds threshold
    if doc.grand_total >= current_threshold:
        # Find Account dynamically
        wht_account = frappe.db.get_value("Account", {"account_name": ["like", "%Withholding%"], "company": doc.company})
        
        if not wht_account:
            return

        # Check for duplicates
        wht_exists = any(t.account_head == wht_account for t in doc.taxes)
        
        if not wht_exists:
            doc.append("taxes", {
                "charge_type": "Actual",
                "account_head": wht_account,
                "description": f"3% WHT (Threshold: {current_threshold:,.0f} ETB)",
                "tax_amount": -(doc.total * 0.03), # Negative because we deduct it
                "category": "Total",               # FIX: Mandatory Field
                "add_deduct_tax": "Deduct"         # FIX: Mandatory Field
            })
            
            doc.calculate_taxes_and_totals()
