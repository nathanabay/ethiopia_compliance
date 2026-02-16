# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt
import unittest
import frappe
from frappe.utils import nowdate, add_days
from ethiopia_compliance.ethiopia_compliance.doctype.wht_certificate.wht_certificate import WHTCertificate
from ethiopia_compliance.ethiopia_compliance.report.pension_contribution_report.pension_contribution_report import execute as execute_pension
from ethiopia_compliance.ethiopia_compliance.report.income_tax_withholding_report.income_tax_withholding_report import execute as execute_income_tax
from ethiopia_compliance.ethiopia_compliance.report.annual_tax_statement.annual_tax_statement import execute as execute_annual_tax

class TestComplianceFeatures(unittest.TestCase):
	def setUp(self):
		# Setup test data if needed
		pass

	def test_excise_tax_fields_exist(self):
		"""Verify Excise Tax fields are present in Item Meta"""
		item_meta = frappe.get_meta("Item")
		self.assertTrue(item_meta.get_field("custom_excise_tax_rate"), "Excise Tax Rate field missing in Item")
		self.assertTrue(item_meta.get_field("custom_excise_tax_category"), "Excise Tax Category field missing in Item")

	def test_fiscal_device_fields_exist(self):
		"""Verify Fiscal Device fields are present in Compliance Setting Meta"""
		setting_meta = frappe.get_meta("Compliance Setting")
		self.assertTrue(setting_meta.get_field("enable_fiscal_device"), "Enable Fiscal Device field missing")
		self.assertTrue(setting_meta.get_field("fiscal_device_type"), "Fiscal Device Type field missing")

	def test_wht_certificate_generation(self):
		"""Test WHT Certificate generation logic"""
		# Create a dummy supplier
		supplier_name = "Test Supplier " + frappe.utils.random_string(5)
		if not frappe.db.exists("Supplier", supplier_name):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": supplier_name, "supplier_group": "All Supplier Groups"}).insert()

		# Create a dummy purchase invoice (mocked)
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"supplier": supplier_name,
			"posting_date": nowdate(),
			"items": [{"item_code": "Test Item", "qty": 1, "rate": 1000}],
			"taxes": [{"charge_type": "Actual", "account_head": "WHT Account", "tax_amount": 20}] # simplified
		})
		# We can't easily submit in unit tests without full setup, so we'll mock the query or rely on existing data
		# For unit test, we can check if the method exists and runs without error on empty data
		
		cert = frappe.new_doc("WHT Certificate")
		cert.supplier = supplier_name
		cert.company = frappe.defaults.get_user_default("Company") or "Bespo"
		cert.period_from = add_days(nowdate(), -30)
		cert.period_to = nowdate()
		
		# Execute the method
		try:
			cert.generate_certificate_data()
			self.assertTrue(True, "generate_certificate_data executed successfully")
		except Exception as e:
			self.fail(f"generate_certificate_data failed with error: {e}")

	def test_payroll_reports_execution(self):
		"""Test that payroll reports execute without error"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"month": "February",
			"year": "2026"
		}
		
		# Test Pension Report
		try:
			columns, data = execute_pension(filters)
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
		except Exception as e:
			self.fail(f"Pension Report execution failed: {e}")

		# Test Income Tax Report
		try:
			columns, data = execute_income_tax(filters)
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
		except Exception as e:
			self.fail(f"Income Tax Report execution failed: {e}")

		# Test Annual Tax Statement
		try:
			columns, data = execute_annual_tax(filters)
			self.assertIsInstance(columns, list)
			self.assertIsInstance(data, list)
		except Exception as e:
			self.fail(f"Annual Tax Statement execution failed: {e}")

