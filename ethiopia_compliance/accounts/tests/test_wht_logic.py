import frappe
from frappe.tests.utils import FrappeTestCase
from ethiopia_compliance.accounts.wht_logic import apply_withholding_tax


class TestWHTLogic(FrappeTestCase):
	"""Prove WHT logic: 30% penalty for missing TIN, standard 3% otherwise."""

	def setUp(self):
		"""Ensure required DB state without using frappe.get_doc for custom doctypes."""
		self.cs_name = "Compliance Setting"

		# Ensure Compliance Setting exists (use db.set_value to avoid controller import)
		if not frappe.db.exists("Compliance Setting", self.cs_name):
			frappe.db.sql("""
				INSERT INTO `tabCompliance Setting` (name, wht_rate, wht_goods_threshold, wht_services_threshold)
				VALUES (%(name)s, 3, 10000, 3000)
			""", {"name": self.cs_name})

		# Ensure baseline values using db.set_value (bypasses controller)
		frappe.db.set_value("Compliance Setting", self.cs_name, "wht_rate", 3)
		frappe.db.set_value("Compliance Setting", self.cs_name, "wht_goods_threshold", 10000)
		frappe.db.set_value("Compliance Setting", self.cs_name, "wht_services_threshold", 3000)

		# Ensure a WHT Account is set
		wht_account = frappe.db.get_value("Compliance Setting", self.cs_name, "wht_account")
		if not wht_account:
			# Find any existing WHT account
			wht_acct = frappe.db.get_value("Account", {
				"account_name": ["like", "%Withholding%"],
				"is_group": 0
			}, "name")
			if wht_acct:
				frappe.db.set_value("Compliance Setting", self.cs_name, "wht_account", wht_acct)

		# Ensure a test Supplier exists with WHT eligibility
		if not frappe.db.exists("Supplier", "_Test WHT Supplier"):
			frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": "_Test WHT Supplier",
				"supplier_group": "All Supplier Groups",
				"custom_wht_eligible": 1,
			}).insert(ignore_permissions=True)

		# Ensure a test item exists
		if not frappe.db.exists("Item", "_Test WHT Item"):
			frappe.get_doc({
				"doctype": "Item",
				"item_code": "_Test WHT Item",
				"item_name": "_Test WHT Item",
				"item_group": "All Item Groups",
				"is_stock_item": 1,
				"stock_uom": "Nos",
			}).insert(ignore_permissions=True)

	def _set_wht_rate(self, rate):
		frappe.db.set_value("Compliance Setting", self.cs_name, "wht_rate", rate)

	def _make_invoice(self, tin):
		"""Create a Purchase Invoice new_doc preset for WHT testing."""
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
		doc = frappe.new_doc("Purchase Invoice")
		doc.supplier = "_Test WHT Supplier"
		doc.company = company
		doc.custom_supplier_tin = tin
		doc.grand_total = 15000
		doc.total = 15000
		doc.append("items", {
			"item_code": "_Test WHT Item",
			"qty": 1,
			"rate": 15000,
			"amount": 15000,
		})
		return doc

	def test_wht_penalty_applied(self):
		"""Purchase Invoice missing supplier TIN -> 30% penalty WHT applied."""
		self._set_wht_rate(3)
		doc = self._make_invoice(tin="")  # Missing TIN triggers 30% penalty

		apply_withholding_tax(doc, None)

		wht_row = None
		for tax in doc.taxes:
			if "30%" in tax.description or "Penalty" in tax.description:
				wht_row = tax
				break

		self.assertIsNotNone(wht_row, "Expected a 30% penalty WHT tax row to be applied")
		expected_tax = -(15000 * 0.30)
		self.assertAlmostEqual(
			wht_row.tax_amount, expected_tax, places=1,
			msg=f"Expected tax amount ~{expected_tax}, got {wht_row.tax_amount}"
		)

	def test_wht_standard_rate(self):
		"""Purchase Invoice with valid TIN -> standard 3% WHT applied."""
		self._set_wht_rate(3)
		doc = self._make_invoice(tin="0012345678")  # Valid TIN

		apply_withholding_tax(doc, None)

		penalty_row = None
		wht_row = None
		for tax in doc.taxes:
			if "Penalty" in tax.description:
				penalty_row = tax
			elif "WHT" in tax.description:
				wht_row = tax

		self.assertIsNone(penalty_row, "No penalty WHT row expected when TIN is present")
		self.assertIsNotNone(wht_row, "Expected a standard WHT tax row to be applied")
		expected_tax = -(15000 * 0.03)
		self.assertAlmostEqual(
			wht_row.tax_amount, expected_tax, places=1,
			msg=f"Expected tax amount ~{expected_tax}, got {wht_row.tax_amount}"
		)
