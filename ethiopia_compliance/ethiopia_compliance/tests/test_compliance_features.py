# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt
import unittest
import frappe
from frappe.utils import nowdate, add_days
from ethiopia_compliance.ethiopia_compliance.doctype.wht_certificate.wht_certificate import WHTCertificate
from ethiopia_compliance.ethiopia_compliance.report.pension_contribution_report.pension_contribution_report import execute as execute_pension
from ethiopia_compliance.ethiopia_compliance.report.income_tax_withholding_report.income_tax_withholding_report import execute as execute_income_tax
from ethiopia_compliance.ethiopia_compliance.report.annual_tax_statement.annual_tax_statement import execute as execute_annual_tax
from ethiopia_compliance.ethiopia_compliance.report.ethiopia_schedule_a.ethiopia_schedule_a import execute as execute_schedule_a
from ethiopia_compliance.ethiopia_compliance.report.sigtas_withholding_report.sigtas_withholding_report import execute as execute_sigtas
from ethiopia_compliance.ethiopia_compliance.report.tass_purchase_declaration.tass_purchase_declaration import execute as execute_tass_purchase
from ethiopia_compliance.ethiopia_compliance.report.tass_sales_declaration.tass_sales_declaration import execute as execute_tass_sales
from ethiopia_compliance.ethiopia_compliance.report.tass_purchase_excel_export.tass_purchase_excel_export import execute as execute_tass_excel


class TestComplianceFeatures(unittest.TestCase):
	def setUp(self):
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
		supplier_name = "Test Supplier " + frappe.utils.random_string(5)
		if not frappe.db.exists("Supplier", supplier_name):
			frappe.get_doc({"doctype": "Supplier", "supplier_name": supplier_name, "supplier_group": "All Supplier Groups"}).insert()

		# Create a dummy purchase invoice (mocked)
		pi = frappe.get_doc({
			"doctype": "Purchase Invoice",
			"supplier": supplier_name,
			"posting_date": nowdate(),
			"items": [{"item_code": "Test Item", "qty": 1, "rate": 1000}],
			"taxes": [{"charge_type": "Actual", "account_head": "WHT Account", "tax_amount": 20}]
		})

		cert = frappe.new_doc("WHT Certificate")
		cert.supplier = supplier_name
		cert.company = frappe.defaults.get_user_default("Company") or "Bespo"
		cert.period_from = add_days(nowdate(), -30)
		cert.period_to = nowdate()

		try:
			cert.generate_certificate_data()
			self.assertTrue(True, "generate_certificate_data executed successfully")
		except Exception as e:
			self.fail(f"generate_certificate_data failed with error: {e}")

	def test_payroll_reports_execution(self):
		"""Test that payroll reports execute without error with valid filters"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"month": "February",
			"year": "2026"
		}

		for name, fn in [
			("Pension Report", execute_pension),
			("Income Tax Report", execute_income_tax),
			("Annual Tax Statement", execute_annual_tax),
		]:
			with self.subTest(name):
				try:
					columns, data = fn(filters)
					self.assertIsInstance(columns, list, f"{name}: columns should be a list")
					self.assertIsInstance(data, list, f"{name}: data should be a list")
				except Exception as e:
					self.fail(f"{name} execution failed: {e}")

	def test_filter_validation_rejects_missing_filters(self):
		"""Reports should raise validation errors when required filters are missing"""
		test_cases = [
			({}, "no filters at all"),
			({"year": "2026"}, "missing company"),
			({"company": "Test"}, "missing year"),
		]
		for invalid_filters, desc in test_cases:
			with self.subTest(desc):
				with self.assertRaises(Exception, msg=f"Annual Tax should reject {desc}"):
					execute_annual_tax(invalid_filters)

	def test_filter_validation_rejects_invalid_month(self):
		"""Payroll reports should reject invalid month names"""
		with self.assertRaises(Exception, msg="Income Tax should reject invalid month"):
			execute_income_tax({"company": "Test", "year": "2026", "month": "NotAMonth"})
		with self.assertRaises(Exception, msg="Pension should reject invalid month"):
			execute_pension({"company": "Test", "year": "2026", "month": ""})

	def test_report_column_structure(self):
		"""Verify each report returns the expected column structure"""
		reports = [
			("Pension Contribution", execute_pension, {"company": "Test", "year": "2026", "month": "February"},
			 ["employee", "employee_name", "pension_number", "basic_salary", "org_pension", "emp_pension", "gross_pay", "total_pension"]),
			("Income Tax Withholding", execute_income_tax, {"company": "Test", "year": "2026", "month": "February"},
			 ["employee", "employee_name", "tin_number", "basic_salary", "taxable_income", "income_tax", "cost_sharing", "net_pay"]),
			("Annual Tax Statement", execute_annual_tax, {"company": "Test", "year": "2026"},
			 ["employee", "employee_name", "tin_number", "total_gross_pay", "total_taxable_income", "total_income_tax", "total_pension", "net_pay"]),
		]
		for name, fn, filters, expected_fields in reports:
			with self.subTest(name):
				columns, data = fn(filters)
				fieldnames = [c["fieldname"] for c in columns]
				for expected in expected_fields:
					self.assertIn(expected, fieldnames, f"{name}: column '{expected}' missing")

	def test_schedule_a_report_execution(self):
		"""Test Ethiopia Schedule A report executes and returns correct columns"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31"
		}
		columns, data = execute_schedule_a(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		fieldnames = [c["fieldname"] for c in columns]
		for expected in ["emp_tin", "emp_name", "basic_salary", "total_taxable", "tax_withheld", "net_pay"]:
			self.assertIn(expected, fieldnames, f"Schedule A: column '{expected}' missing")

	def test_tass_purchase_declaration_execution(self):
		"""Test TASS Purchase Declaration report executes"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31"
		}
		columns, data = execute_tass_purchase(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		fieldnames = [c["fieldname"] for c in columns]
		for expected in ["purchaser_tin", "seller_tin", "receipt_no", "amount", "purchase_type"]:
			self.assertIn(expected, fieldnames, f"TASS Purchase: column '{expected}' missing")

	def test_tass_sales_declaration_execution(self):
		"""Test TASS Sales Declaration report executes"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31"
		}
		columns, data = execute_tass_sales(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		fieldnames = [c["fieldname"] for c in columns]
		for expected in ["seller_tin", "buyer_tin", "buyer_name", "inv_no", "doctype", "fs_no", "net_total", "tax_amount", "amount"]:
			self.assertIn(expected, fieldnames, f"TASS Sales: column '{expected}' missing")

	def test_tass_purchase_excel_export_execution(self):
		"""Test TASS Purchase Excel Export report executes"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31"
		}
		columns, data = execute_tass_excel(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		fieldnames = [c["fieldname"] for c in columns]
		for expected in ["tin", "name", "inv_no", "total", "p_type"]:
			self.assertIn(expected, fieldnames, f"TASS Excel Export: column '{expected}' missing")

	def test_sigtas_withholding_report_execution(self):
		"""Test SIGTAS Withholding Report executes and returns rate column from tax table"""
		filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2026-01-01",
			"to_date": "2026-01-31"
		}
		columns, data = execute_sigtas(filters)
		self.assertIsInstance(columns, list)
		self.assertIsInstance(data, list)
		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("rate", fieldnames, "SIGTAS: 'rate' column should be present")

	def test_all_reports_handle_empty_data(self):
		"""All reports should return empty data gracefully (no crashes)"""
		future_filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"from_date": "2099-12-01",
			"to_date": "2099-12-31"
		}
		payroll_filters = {
			"company": frappe.defaults.get_user_default("Company") or "Bespo",
			"month": "December",
			"year": "2099"
		}

		for name, fn, filters in [
			("SIGTAS", execute_sigtas, future_filters),
			("TASS Purchase", execute_tass_purchase, future_filters),
			("TASS Sales", execute_tass_sales, future_filters),
			("TASS Excel Export", execute_tass_excel, future_filters),
			("Schedule A", execute_schedule_a, future_filters),
			("Pension", execute_pension, payroll_filters),
			("Income Tax", execute_income_tax, payroll_filters),
			("Annual Tax", execute_annual_tax, {"company": "Test", "year": "2099"}),
		]:
			with self.subTest(name):
				try:
					columns, data = fn(filters)
					self.assertIsInstance(data, list, f"{name}: should return list for empty data")
				except Exception as e:
					self.fail(f"{name}: crashed on empty data: {e}")

	def test_no_fabricated_pension_fallback(self):
		"""Pension report should not fabricate pension numbers from basic salary"""
		filters = {"company": "Test", "year": "2099", "month": "December"}
		columns, data = execute_pension(filters)
		for row in data:
			self.assertEqual(row.get("org_pension", 0), 0,
				"Pension report should not fabricate employer pension numbers when no data exists")
			self.assertEqual(row.get("emp_pension", 0), 0,
				"Pension report should not fabricate employee pension numbers when no data exists")
