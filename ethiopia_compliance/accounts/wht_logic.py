import frappe
from frappe import _
from frappe.utils import flt


def apply_withholding_tax(doc, method):
    """Apply Withholding Tax (WHT) based on Compliance Settings.

    Hooked to Purchase Invoice before_save.
    Proclamation No. 979/2016 Art. 97 as amended by Proclamation No. 1395/2017.

    WHT Thresholds (from Compliance Setting):
        - Goods:    wht_goods_threshold  (default 20,000 ETB)
        - Services: wht_services_threshold (default 10,000 ETB)

    WHT Rates (from Compliance Setting):
        - Standard domestic rate: wht_rate (default 3%)
        - Punitive rate (missing/invalid supplier TIN): punitive_wht_rate (default 30%)

    Article 97 trigger:
        - Goods: transaction > 20,000 ETB
        - Services: transaction > 10,000 ETB
    """
    # 1. Skip if supplier is not WHT eligible
    supplier_wht = frappe.db.get_value("Supplier", doc.supplier, "custom_wht_eligible")
    if not supplier_wht:
        return

    # 2. Fetch Compliance Settings (cached)
    settings = frappe.get_cached_doc("Compliance Setting")

    goods_threshold   = flt(settings.wht_goods_threshold) or 20000
    services_threshold = flt(settings.wht_services_threshold) or 10000
    standard_rate  = (flt(settings.wht_rate) or 3) / 100
    punitive_rate  = (flt(settings.punitive_wht_rate) or 30) / 100

    # 3. Determine current threshold — goods vs services
    current_threshold = goods_threshold
    if doc.items:
        item_codes = list({item.item_code for item in doc.items if item.item_code})
        if item_codes:
            # Single query: batch-fetch is_stock_item for all items in this invoice
            is_stock_map = dict(
                frappe.get_values("Item", item_codes, ["name", "is_stock_item"])
            )
            for item in doc.items:
                if not is_stock_map.get(item.item_code, True):
                    current_threshold = services_threshold
                    break

    # 4. Determine WHT rate — punitive if supplier TIN is missing or structurally invalid
    rate = standard_rate
    penalty_applied = False

    from ethiopia_compliance.utils.tin_validator import is_supplier_tin_valid
    if not is_supplier_tin_valid(doc.supplier):
        rate = punitive_rate
        penalty_applied = True

    # 5. Apply WHT if grand total exceeds threshold
    if doc.grand_total >= current_threshold:
        wht_account = settings.wht_account
        if not wht_account:
            wht_account = frappe.db.get_value(
                "Account",
                {"account_name": ["like", "%Withholding%"], "company": doc.company, "is_group": 0}
            )

        if not wht_account:
            return

        # Check for duplicate WHT entry
        wht_exists = any(t.account_head == wht_account for t in doc.taxes)
        if wht_exists:
            return

        if penalty_applied:
            desc = _(
                "30% Penalty WHT — Missing/Invalid Supplier TIN "
                "(Proclamation No. 1395/2017 Art. 97)"
            )
        else:
            desc = _(
                "{0}% WHT (Threshold: {1:,.0f} ETB | "
                "Proclamation No. 979/2016 Art. 97)"
            ).format(int(settings.wht_rate or 3), current_threshold)

        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": wht_account,
            "description": desc,
            "tax_amount": -(doc.total * rate),
            "category": "Total",
            "add_deduct_tax": "Deduct"
        })

        doc.calculate_taxes_and_totals()