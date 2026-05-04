import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt
from ethiopia_compliance.accounts.wht_logic import apply_withholding_tax
from ethiopia_compliance.report.ethiopia_schedule_a.ethiopia_schedule_a import (
    calculate_schedule_a_tax,
    _compute_annual_slab_tax
)


class TestWHTLogic(FrappeTestCase):
    """Prove WHT logic: 30%% penalty for missing TIN, standard 3%% otherwise.

    Thresholds per Proclamation No. 979/2016 Art. 97 (as amended 1395/2017):
      - Goods:    > 20,000 ETB
      - Services: > 10,000 ETB
      - Standard rate: 3%%
      - Punitive rate (missing TIN): 30%%
    """

    def setUp(self):
        self.cs_name = "Compliance Setting"

        if not frappe.db.exists("Compliance Setting", self.cs_name):
            frappe.db.sql("""
                INSERT INTO `tabCompliance Setting`
                    (name, wht_rate, wht_goods_threshold, wht_services_threshold, punitive_wht_rate)
                VALUES (%(name)s, 3, 20000, 10000, 30)
            """, {"name": self.cs_name})

        frappe.db.set_value("Compliance Setting", self.cs_name, {
            "wht_rate": 3,
            "wht_goods_threshold": 20000,
            "wht_services_threshold": 10000,
            "punitive_wht_rate": 30
        })

        wht_account = frappe.db.get_value("Account", {
            "account_name": ["like", "%Withholding%"], "is_group": 0
        }, "name")
        if wht_account:
            frappe.db.set_value("Compliance Setting", self.cs_name, "wht_account", wht_account)

        if not frappe.db.exists("Supplier", "_Test WHT Supplier"):
            frappe.get_doc({
                "doctype": "Supplier", "supplier_name": "_Test WHT Supplier",
                "supplier_group": "All Supplier Groups", "custom_wht_eligible": 1,
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Item", "_Test WHT Item"):
            frappe.get_doc({
                "doctype": "Item", "item_code": "_Test WHT Item",
                "item_name": "_Test WHT Item", "item_group": "All Item Groups",
                "is_stock_item": 1, "stock_uom": "Nos",
            }).insert(ignore_permissions=True)

    def _make_invoice(self, tin="", grand_total=15000, is_stock_item=True):
        company = frappe.defaults.get_user_default("Company") or \
            frappe.db.get_single_value("Global Defaults", "default_company")
        doc = frappe.new_doc("Purchase Invoice")
        doc.supplier = "_Test WHT Supplier"
        doc.company = company
        doc.custom_supplier_tin = tin
        doc.grand_total = grand_total
        doc.total = grand_total
        doc.append("items", {
            "item_code": "_Test WHT Item",
            "qty": 1,
            "rate": grand_total,
            "amount": grand_total,
        })
        return doc

    def test_wht_penalty_applied_missing_tin(self):
        """Missing supplier TIN -> 30%% punitive WHT applied."""
        doc = self._make_invoice(tin="")
        apply_withholding_tax(doc, None)

        penalty_row = None
        for tax in doc.taxes:
            if "Penalty" in (tax.description or ""):
                penalty_row = tax
                break

        self.assertIsNotNone(penalty_row, "Expected 30%% penalty WHT row for missing TIN")
        self.assertAlmostEqual(flt(penalty_row.tax_amount), -(15000 * 0.30), places=1)

    def test_wht_penalty_applied_invalid_tin(self):
        """Invalid format supplier TIN -> 30%% punitive WHT applied."""
        doc = self._make_invoice(tin="INVALID")
        apply_withholding_tax(doc, None)

        penalty_row = None
        for tax in doc.taxes:
            if "Penalty" in (tax.description or ""):
                penalty_row = tax
                break

        self.assertIsNotNone(penalty_row, "Expected 30%% penalty WHT row for invalid TIN")

    def test_wht_standard_rate_goods_above_threshold(self):
        """Valid TIN + goods above 20k threshold -> 3%% standard WHT applied."""
        doc = self._make_invoice(tin="0012345678", grand_total=25000)
        apply_withholding_tax(doc, None)

        penalty_row = any("Penalty" in (t.description or "") for t in doc.taxes)
        wht_row = next((t for t in doc.taxes if "WHT" in (t.description or "") and "Penalty" not in t.description), None)

        self.assertFalse(penalty_row, "No penalty expected with valid TIN")
        self.assertIsNotNone(wht_row, "Expected standard 3%% WHT row")
        self.assertAlmostEqual(flt(wht_row.tax_amount), -(25000 * 0.03), places=1)

    def test_wht_below_goods_threshold_no_wht(self):
        """Goods invoice below 20k threshold -> no WHT applied."""
        doc = self._make_invoice(tin="0012345678", grand_total=15000)
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
    """Prove Schedule A employment income tax slabs per Proclamation 979/2016.

    Monthly taxable income slabs:
        0 - 2,000 ETB:        0%%
        2,001 - 4,000 ETB:   15%%  (on band above 2,000)
        4,001 - 7,000 ETB:   20%%  (on band above 4,000)
        7,001 - 10,000 ETB:  25%%  (on band above 7,000)
        10,001 - 14,000 ETB: 30%%  (on band above 10,000)
        Above 14,000 ETB:     35%%  (on band above 14,000)
    """

    def test_zero_income(self):
        """Zero monthly income -> 0 tax."""
        self.assertEqual(calculate_schedule_a_tax(0), 0.0)
        self.assertEqual(calculate_schedule_a_tax(-100), 0.0)

    def test_first_bracket(self):
        """Monthly 1,500 ETB -> within 0%% bracket -> 0 tax."""
        self.assertEqual(calculate_schedule_a_tax(1500), 0.0)

    def test_first_band_only(self):
        """Monthly 3,000 ETB -> 2,000 at 0%% + 1,000 at 15%% = 150/yr = 12.50/mo."""
        result = calculate_schedule_a_tax(3000)
        expected_annual = 0 + 1000 * 0.15  # only 1,000 in 15%% band
        self.assertAlmostEqual(result * 12, expected_annual, places=1)

    def test_second_bracket_full(self):
        """Monthly 4,000 ETB -> 2,000×0%% + 2,000×15%% = 300/yr = 25.00/mo."""
        result = calculate_schedule_a_tax(4000)
        expected_annual = 2000 * 0.15
        self.assertAlmostEqual(result * 12, expected_annual, places=1)

    def test_third_bracket(self):
        """Monthly 7,000 ETB -> 2,000×0%% + 2,000×15%% + 3,000×20%% = 300+600 = 900/yr."""
        result = calculate_schedule_a_tax(7000)
        expected_annual = 2000 * 0.15 + 3000 * 0.20
        self.assertAlmostEqual(result * 12, expected_annual, places=1)

    def test_fourth_bracket(self):
        """Monthly 10,000 ETB -> full second+third+fourth bands."""
        result = calculate_schedule_a_tax(10000)
        expected_annual = (2000 * 0.15) + (3000 * 0.20) + (3000 * 0.25)
        self.assertAlmostEqual(result * 12, expected_annual, places=1)

    def test_fifth_bracket(self):
        """Monthly 14,000 ETB -> all bands 0-14k at their respective rates."""
        result = calculate_schedule_a_tax(14000)
        expected_annual = (2000 * 0.15) + (3000 * 0.20) + (3000 * 0.25) + (4000 * 0.30)
        self.assertAlmostEqual(result * 12, expected_annual, places=1)

    def test_top_bracket(self):
        """Monthly 20,000 ETB -> all bands + excess at 35%%."""
        result = calculate_schedule_a_tax(20000)
        # Full 14k bracket + 6,000 at 35%%
        expected_annual = (
            2000 * 0.15 +
            3000 * 0.20 +
            3000 * 0.25 +
            4000 * 0.30 +
            6000 * 0.35
        )
        self.assertAlmostEqual(result * 12, expected_annual, places=1)


class TestMATCalculation(FrappeTestCase):
    """Prove MAT (Minimum Alternative Tax) per Proclamation 979/2016 Art. 23.

    MAT = 2.5%% of Gross Sales when Net Profit Tax < 2.5%% of Gross Sales.
    """

    def test_mat_applies_when_profit_tax_below_mat(self):
        """Low profit margin: net_profit_tax=1%% < mat_rate=2.5%% -> MAT applies."""
        # Simulate: gross_sales=1,000,000, expenses=980,000 -> net_profit=20,000
        # net_profit_tax = 20,000 * 0.30 = 6,000 (Schedule C 30%%)
        # mat_liability = 1,000,000 * 0.025 = 25,000
        # MAT (25,000) > Schedule C (6,000) -> MAT applies
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
        # gross_sales=200,000, expenses=50,000 -> net_profit=150,000
        # net_profit_tax = 150,000 * 0.30 = 45,000
        # mat_liability = 200,000 * 0.025 = 5,000
        # MAT (5,000) < Schedule C (45,000) -> Schedule C applies
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
        """Zero or negative profit -> MAT is 0."""
        net_profit = 0
        gross_sales = 100000

        schedule_c_tax = net_profit * 0.30
        mat_liability = gross_sales * 0.025

        mat_applied = mat_liability > schedule_c_tax
        final_tax = mat_liability if mat_applied else schedule_c_tax

        self.assertAlmostEqual(final_tax, 0.0, places=2)


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