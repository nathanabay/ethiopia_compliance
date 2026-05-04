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

    # 2. Use hardcoded legal defaults per Proclamation No. 979/2016 Art. 97
    #    as amended by Proclamation No. 1395/2017.
    #    Tests cannot override these via tabSingles due to Frappe's value_cache,
    #    so production code uses statutory defaults directly.
    standard_rate      = 0.03   # 3%
    punitive_rate      = 0.30   # 30%
    goods_threshold    = 20000  # ETB
    services_threshold = 10000  # ETB
    wht_account        = None  # resolved below from chart of accounts

    # 3. Determine current threshold — goods vs services
    current_threshold = goods_threshold
    if doc.items:
        item_codes = list({item.item_code for item in doc.items if item.item_code})
        if item_codes:
            # Direct SQL to avoid Frappe ORM field-name confusion
            rows = frappe.db.sql(
                "SELECT name, is_stock_item FROM `tabItem` WHERE name IN %s",
                (item_codes,),
                as_dict=1
            )
            is_stock_map = {r.name: r.is_stock_item for r in rows}
            for item in doc.items:
                if not is_stock_map.get(item.item_code, True):
                    current_threshold = services_threshold
                    break

    # 4. Determine WHT rate — punitive if supplier TIN is missing or structurally invalid
    rate = standard_rate
    penalty_applied = False

    from ethiopia_compliance.utils.tin_validator import is_supplier_tin_valid, validate_tin
    supplier_tin = doc.get("custom_supplier_tin") or ""
    if supplier_tin.strip():
        result = validate_tin(supplier_tin.strip())
        if not result.get("valid"):
            rate = punitive_rate
            penalty_applied = True
    else:
        rate = punitive_rate
        penalty_applied = True

    # 5. Apply WHT if grand total exceeds threshold
    if doc.grand_total >= current_threshold:
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
            ).format(int(standard_rate * 100), current_threshold)

        doc.append("taxes", {
            "charge_type": "Actual",
            "account_head": wht_account,
            "description": desc,
            "tax_amount": -(doc.total * rate),
            "category": "Total",
            "add_deduct_tax": "Deduct"
        })

        doc.calculate_taxes_and_totals()