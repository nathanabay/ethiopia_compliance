import frappe

def apply_withholding_tax(doc, method):
    """
    Applies Withholding Tax (WHT) based on Compliance Settings.
    """
    # 1. Check if Supplier is WHT Eligible
    supplier_wht = frappe.db.get_value("Supplier", doc.supplier, "custom_wht_eligible")
    if not supplier_wht:
        return

    # 2. Fetch Compliance Settings
    settings = frappe.get_single("Compliance Setting")
    
    # Defaults
    goods_threshold = settings.wht_goods_threshold or 10000
    services_threshold = settings.wht_services_threshold or 3000
    wht_rate = (settings.wht_rate or 2) / 100

    # 3. Determine Threshold based on Item Types
    current_threshold = goods_threshold # Default to Goods
    
    for item in doc.items:
        is_stock = frappe.db.get_value("Item", item.item_code, "is_stock_item")
        if not is_stock:
            current_threshold = services_threshold # Strict service threshold
            break 

    # 4. Apply Tax if Grand Total exceeds threshold
    if doc.grand_total >= current_threshold:
        # Find Account dynamically
        wht_account = settings.wht_account or frappe.db.get_value("Account", {"account_name": ["like", "%Withholding%"], "company": doc.company})
        
        if not wht_account:
            return

        # Check for duplicates
        wht_exists = any(t.account_head == wht_account for t in doc.taxes)
        
        if not wht_exists:
            doc.append("taxes", {
                "charge_type": "Actual",
                "account_head": wht_account,
                "description": f"{settings.wht_rate or 2}% WHT (Threshold: {current_threshold:,.0f} ETB)",
                "tax_amount": -(doc.total * wht_rate), # Negative because we deduct it
                "category": "Total",               
                "add_deduct_tax": "Deduct"         
            })
            
            doc.calculate_taxes_and_totals()
