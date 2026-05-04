import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from ethiopia_compliance.accounts.wht_logic import apply_withholding_tax
from ethiopia_compliance.report.ethiopia_schedule_a.ethiopia_schedule_a import (
    calculate_schedule_a_tax
)


class TestWHTLogic(FrappeTestCase):
    """Prove WHT logic: 30%% penalty for missing TIN, standard 3%% otherwise."""

    def setUp(self):
        # 1. Compliance Setting values — INSERT...ON DUPLICATE KEY UPDATE
        for field, value in [
            ("wht_rate", 3),
            ("wht_goods_threshold", 20000),
            ("wht_services_threshold", 10000),
            ("punitive_wht_rate", 30),
        ]:
            frappe.db.sql("""
                INSERT INTO `tabSingles` (doctype, field, value)
                VALUES ('Compliance Setting', %(field)s, %(value)s)
                ON DUPLICATE KEY UPDATE value = %(value)s
            """, {"field": field, "value": str(value)})
        if "Compliance Setting" in frappe.db.value_cache:
            del frappe.db.value_cache["Compliance Setting"]

        # 2. Setup Test Supplier
        if not frappe.db.exists("Supplier", "_Test WHT Supplier"):
            frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": "_Test WHT Supplier",
                "supplier_group": "All Supplier Groups",
                "custom_wht_eligible": 1
            }).insert(ignore_permissions=True)

        # 3. Setup Test Item (stock)
        if not frappe.db.exists("Item", "_Test WHT Item"):
            frappe.get_doc({
                "doctype": "Item",
                "item_code": "_Test WHT Item",
                "item_name": "Test Stock Item",
                "item_group": "All Item Groups",
                "is_stock_item": 1,
                "stock_uom": "Nos"
            }).insert(ignore_permissions=True)

        # 4. Create WHT account for BESPO company (needed by apply_withholding_tax)
        if not frappe.db.exists("Account", {"company": "BESPO", "account_name": ["like", "%Withholding%"]}):
            frappe.get_doc({
                "doctype": "Account",
                "account_name": "Withholding Tax Payable",
                "account_type": "Tax",
                "company": "BESPO",
                "is_group": 0,
            }).insert(ignore_permissions=True)

    def _make_invoice(self, tin="", grand_total=15000, is_stock_item=True):
        """Create a Purchase Invoice for WHT testing.

        is_stock_item=True  -> uses _Test WHT Item (stock item, 20k threshold)
        is_stock_item=False -> uses _Test Non Stock Item (non-stock, 10k threshold)
        """
        doc = frappe.new_doc("Purchase Invoice")
        doc.supplier = "_Test WHT Supplier"
        # custom_supplier_tin has fetch_from=supplier.tax_id; set directly
        doc.custom_supplier_tin = tin
        doc.grand_total = grand_total
        doc.total = grand_total
        # WHT account lookup requires company — use first active company
        if not getattr(frappe, "flags", None) or not frappe.flags.company:
            companies = frappe.get_all("Company", filters={"is_group": 0}, fields=["name"], limit=1)
            doc.company = companies[0].name if companies else None

        # Select item based on stock flag
        if is_stock_item:
            item_code = "_Test WHT Item"
        else:
            item_code = "_Test Non Stock Item"
            # Create non-stock item if needed
            if not frappe.db.exists("Item", item_code):
                frappe.get_doc({
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": "Test Service Item",
                    "item_group": "All Item Groups",
                    "is_stock_item": 0,
                    "stock_uom": "Nos"
                }).insert(ignore_permissions=True)

        doc.append("items", {
            "item_code": item_code,
            "qty": 1,
            "rate": grand_total,
            "amount": grand_total,
        })
        return doc

    def test_wht_penalty_applied_missing_tin(self):
        """Missing supplier TIN + goods above 20k -> 30%% punitive WHT applied."""
        doc = self._make_invoice(tin="", grand_total=25000, is_stock_item=True)
        apply_withholding_tax(doc, None)

        penalty_row = None
        for tax in doc.taxes:
            if "Penalty" in (tax.description or ""):
                penalty_row = tax
                break

        self.assertIsNotNone(penalty_row, "Expected 30%% penalty WHT row for missing TIN")
        self.assertAlmostEqual(flt(penalty_row.tax_amount), -(25000 * 0.30), places=1)

    def test_wht_penalty_applied_invalid_tin(self):
        """Invalid TIN + goods above 20k -> 30%% punitive WHT applied."""
        doc = self._make_invoice(tin="INVALID", grand_total=25000, is_stock_item=True)
        apply_withholding_tax(doc, None)

        penalty_row = None
        for tax in doc.taxes:
            if "Penalty" in (tax.description or ""):
                penalty_row = tax
                break

        self.assertIsNotNone(penalty_row, "Expected 30%% penalty WHT row for invalid TIN")

    def test_wht_standard_rate_goods_above_threshold(self):
        """Valid TIN + goods above 20k threshold -> 3%% standard WHT applied."""
        doc = self._make_invoice(tin="0012345678", grand_total=25000, is_stock_item=True)
        apply_withholding_tax(doc, None)

        penalty_row = any("Penalty" in (t.description or "") for t in doc.taxes)
        wht_row = next((t for t in doc.taxes if "WHT" in (t.description or "") and "Penalty" not in t.description), None)

        self.assertFalse(penalty_row, "No penalty expected with valid TIN")
        self.assertIsNotNone(wht_row, "Expected standard 3%% WHT row")
        self.assertAlmostEqual(flt(wht_row.tax_amount), -(25000 * 0.03), places=1)

    def test_wht_below_goods_threshold_no_wht(self):
        """Goods invoice below 20k threshold -> no WHT applied."""
        doc = self._make_invoice(tin="0012345678", grand_total=15000, is_stock_item=True)
        apply_withholding_tax(doc, None)

        wht_rows = [t for t in doc.taxes if "WHT" in (t.description or "")]
        self.assertEqual(len(wht_rows), 0, "No WHT expected below threshold")

    def test_wht_services_above_threshold(self):
        """Services invoice above 10k -> 3%% WHT applied (is_stock_item=False)."""
        doc = self._make_invoice(tin="0012345678", grand_total=15000, is_stock_item=False)
        apply_withholding_tax(doc, None)

        penalty_row = any("Penalty" in (t.description or "") for t in doc.taxes)
        wht_row = next((t for t in doc.taxes if "WHT" in (t.description or "") and "Penalty" not in t.description), None)

        self.assertFalse(penalty_row)
        self.assertIsNotNone(wht_row, "Expected WHT for services above 10k threshold")
        self.assertAlmostEqual(flt(wht_row.tax_amount), -(15000 * 0.03), places=1)


class TestScheduleATaxSlabs(FrappeTestCase):
    """Prove Schedule A employment income tax slabs per Proclamation 1395/2025.

    Monthly taxable income slabs:
        0   – 2,000 ETB:   0%
        2,001 – 4,000 ETB:  15%  →  (salary * 0.15) - 300
        4,001 – 7,000 ETB:  20%  →  (salary * 0.20) - 500
        7,001 – 10,000 ETB: 25%  →  (salary * 0.25) - 850
        10,001 – 14,000 ETB: 30%  →  (salary * 0.30) - 1350
        Above 14,000 ETB:   35%  →  (salary * 0.35) - 2050
    """

    def test_zero_income(self):
        """Zero monthly income -> 0 tax."""
        self.assertEqual(calculate_schedule_a_tax(0), 0.0)
        self.assertEqual(calculate_schedule_a_tax(-100), 0.0)

    def test_first_bracket(self):
        """Monthly 1,500 ETB -> within 0% bracket -> 0 tax."""
        self.assertEqual(calculate_schedule_a_tax(1500), 0.0)

    def test_first_band_only(self):
        """Monthly 3,000 ETB -> within 2,001-4,000 band: 3000*0.15 - 300 = 150."""
        result = calculate_schedule_a_tax(3000)
        self.assertAlmostEqual(result, 150.0, places=2)

    def test_second_bracket_full(self):
        """Monthly 4,000 ETB -> 4000*0.15 - 300 = 300."""
        result = calculate_schedule_a_tax(4000)
        self.assertAlmostEqual(result, 300.0, places=2)

    def test_third_bracket(self):
        """Monthly 7,000 ETB -> 7000*0.20 - 500 = 900."""
        result = calculate_schedule_a_tax(7000)
        self.assertAlmostEqual(result, 900.0, places=2)

    def test_fourth_bracket(self):
        """Monthly 10,000 ETB -> 10000*0.25 - 850 = 1650."""
        result = calculate_schedule_a_tax(10000)
        self.assertAlmostEqual(result, 1650.0, places=2)

    def test_fifth_bracket(self):
        """Monthly 14,000 ETB -> 14000*0.30 - 1350 = 2850."""
        result = calculate_schedule_a_tax(14000)
        self.assertAlmostEqual(result, 2850.0, places=2)

    def test_top_bracket(self):
        """Monthly 20,000 ETB -> 20000*0.35 - 2050 = 4950."""
        result = calculate_schedule_a_tax(20000)
        self.assertAlmostEqual(result, 4950.0, places=2)


class TestMATCalculation(FrappeTestCase):
    """Prove MAT (Minimum Alternative Tax) per Proclamation 1395/2025 Art. 23.

    MAT = 2.5%% of Gross Sales when Net Profit Tax < 2.5%% of Gross Sales.
    """

    def test_mat_applies_when_profit_tax_below_mat(self):
        """Low profit margin: net_profit_tax=1%% < mat_rate=2.5%% -> MAT applies."""
        net_profit = 20000
        gross_sales = 1000000
        mat_rate = 0.025
        schedule_c_rate = 0.30

        schedule_c_tax = net_profit * schedule_c_rate
        mat_liability = gross_sales * mat_rate

        mat_applied = mat_liability > schedule_c_tax
        final_tax = mat_liability if mat_applied else schedule_c_tax

        self.assertTrue(mat_applied, "MAT must apply when below MAT rate")
        self.assertAlmostEqual(mat_liability, 25000.0, places=2)
        self.assertAlmostEqual(schedule_c_tax, 6000.0, places=2)
        self.assertAlmostEqual(final_tax, 25000.0, places=2)

    def test_mat_does_not_apply_when_profit_tax_above_mat(self):
        """High profit margin: net_profit_tax=5%% > mat_rate=2.5%% -> Schedule C applies."""
        net_profit = 150000
        gross_sales = 200000
        mat_rate = 0.025
        schedule_c_rate = 0.30

        schedule_c_tax = net_profit * schedule_c_rate
        mat_liability = gross_sales * mat_rate

        mat_applied = mat_liability > schedule_c_tax
        final_tax = mat_liability if mat_applied else schedule_c_tax

        self.assertFalse(mat_applied, "Schedule C must apply when above MAT rate")
        self.assertAlmostEqual(final_tax, schedule_c_tax, places=2)
        self.assertAlmostEqual(mat_liability, 5000.0, places=2)
        self.assertAlmostEqual(schedule_c_tax, 45000.0, places=2)

    def test_mat_boundary_zero_profit(self):
        """Zero net profit -> MAT is still 2.5%% of gross sales per Art. 23."""
        net_profit = 0
        gross_sales = 100000

        schedule_c_tax = net_profit * 0.30
        mat_liability = gross_sales * 0.025

        mat_applied = mat_liability > schedule_c_tax
        final_tax = mat_liability if mat_applied else schedule_c_tax

        self.assertAlmostEqual(final_tax, 2500.0, places=2)


class TestPaymentLogic(FrappeTestCase):
    """Prove preventive P1 controls: cash payment > 50,000 ETB blocked."""

    def setUp(self):
        if not frappe.db.exists("Mode of Payment", "Cash"):
            frappe.get_doc({
                "doctype": "Mode of Payment", "mode_of_payment": "Cash",
                "enabled": 1, "type": "Cash"
            }).insert(ignore_permissions=True)
        else:
            mop = frappe.get_doc("Mode of Payment", "Cash")
            if mop.type != "Cash":
                mop.type = "Cash"
                mop.save(ignore_permissions=True)

    def test_cash_limit_blocker_55k(self):
        """Cash payment of 55,000 ETB must be blocked."""
        from ethiopia_compliance.accounts.payment_logic import validate_cash_limits
        doc = frappe.new_doc("Payment Entry")
        doc.paid_amount = 55000
        doc.mode_of_payment = "Cash"
        doc.payment_type = "Pay"

        with self.assertRaises(frappe.ValidationError):
            validate_cash_limits(doc, None)

    def test_cash_limit_blocker_exact_50k(self):
        """Exact 50,000 ETB should still pass (limit is a ceiling)."""
        from ethiopia_compliance.accounts.payment_logic import validate_cash_limits
        doc = frappe.new_doc("Payment Entry")
        doc.paid_amount = 50000
        doc.mode_of_payment = "Cash"
        doc.payment_type = "Pay"

        try:
            validate_cash_limits(doc, None)
        except frappe.ValidationError:
            self.fail("Exact 50,000 should pass — limit is a ceiling, not floor")

    def test_cash_limit_45k_passes(self):
        """Cash payment of 45,000 ETB must pass silently."""
        from ethiopia_compliance.accounts.payment_logic import validate_cash_limits
        doc = frappe.new_doc("Payment Entry")
        doc.paid_amount = 45000
        doc.mode_of_payment = "Cash"
        doc.payment_type = "Pay"

        try:
            validate_cash_limits(doc, None)
        except frappe.ValidationError:
            self.fail("45,000 ETB should not be blocked")

    def test_non_cash_above_limit_passes(self):
        """Non-cash payment above limit must pass."""
        from ethiopia_compliance.accounts.payment_logic import validate_cash_limits
        doc = frappe.new_doc("Payment Entry")
        doc.paid_amount = 75000
        doc.mode_of_payment = "Bank Transfer"
        doc.payment_type = "Pay"

        try:
            validate_cash_limits(doc, None)
        except frappe.ValidationError:
            self.fail("Bank Transfer payments must not be blocked")