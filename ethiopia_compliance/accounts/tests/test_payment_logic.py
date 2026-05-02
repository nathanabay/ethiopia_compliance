import frappe
from frappe.tests.utils import FrappeTestCase
from ethiopia_compliance.accounts.payment_logic import validate_cash_limits


class TestPaymentLogic(FrappeTestCase):
	"""Prove preventive P1 controls: cash payment > 50,000 ETB blocked."""

	def setUp(self):
		# Ensure a Cash Mode of Payment exists
		if not frappe.db.exists("Mode of Payment", "Cash"):
			frappe.get_doc({
				"doctype": "Mode of Payment",
				"mode_of_payment": "Cash",
				"enabled": 1,
				"type": "Cash"
			}).insert(ignore_permissions=True)
		else:
			# Ensure the existing Cash MOP has type = Cash
			mop = frappe.get_doc("Mode of Payment", "Cash")
			if mop.type != "Cash":
				mop.type = "Cash"
				mop.save(ignore_permissions=True)

	def test_cash_limit_blocker(self):
		"""Cash payment of 55,000 ETB must throw."""
		doc = frappe.new_doc("Payment Entry")
		doc.paid_amount = 55000
		doc.mode_of_payment = "Cash"

		with self.assertRaises(frappe.ValidationError):
			validate_cash_limits(doc, None)

	def test_cash_limit_pass(self):
		"""Cash payment of 45,000 ETB must pass silently."""
		doc = frappe.new_doc("Payment Entry")
		doc.paid_amount = 45000
		doc.mode_of_payment = "Cash"

		# Should not raise
		try:
			validate_cash_limits(doc, None)
		except frappe.ValidationError:
			self.fail("validate_cash_limits raised ValidationError unexpectedly for 45,000 ETB")

	def test_non_cash_payment_passes(self):
		"""Non-cash payment above limit must pass."""
		doc = frappe.new_doc("Payment Entry")
		doc.paid_amount = 75000
		doc.mode_of_payment = "Bank Transfer"

		try:
			validate_cash_limits(doc, None)
		except frappe.ValidationError:
			self.fail("validate_cash_limits raised ValidationError for non-cash payment")

	def test_missing_mode_of_payment_passes(self):
		"""Payment with no mode_of_payment skips validation."""
		doc = frappe.new_doc("Payment Entry")
		doc.paid_amount = 75000
		doc.mode_of_payment = None

		try:
			validate_cash_limits(doc, None)
		except frappe.ValidationError:
			self.fail("validate_cash_limits raised for missing mode_of_payment")
