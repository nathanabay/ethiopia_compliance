# Ministry of Revenues Export Engine
# Generates VAT XML and Darash CSV files for tax filing

import frappe
from frappe import _
from frappe.utils import cstr, flt, getdate
import csv
import io
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


# ──────────────────────────────────────────
# Header mappings for Darash CSV export
# Maps Frappe fieldnames → Darash-compliant column headers
# ──────────────────────────────────────────

DARASH_HEADERS = {
	# TASS Sales Declaration
	"seller_tin": "Seller TIN",
	"buyer_tin": "Buyer TIN",
	"buyer_tin_status": "TIN Status",
	"buyer_name": "Buyer Name",
	"inv_no": "Invoice Number",
	"mrc": "MRC (Machine Code)",
	"fs_no": "FS Number",
	"date": "Transaction Date",
	"net_total": "Net Total",
	"tax_amount": "Tax Amount",
	"amount": "Grand Total",
	"doctype": "Document Type",
	# TASS Purchase Declaration
	"purchaser_tin": "Purchaser TIN",
	"receipt_no": "Receipt Number",
	"receipt_date": "Receipt Date",
	"calendar_type": "Calendar (G/E)",
	"purchase_type": "Purchase Type (Goods/Services)",
	# SIGTAS Withholding
	"tin": "Supplier TIN",
	"tin_status": "TIN Status",
	"name": "Supplier Name",
	"taxable": "Taxable Amount",
	"rate": "WHT Rate (%)",
	"wht_amount": "Tax Withheld",
	# Generic
	"seller_name": "Seller Name",
}


# ──────────────────────────────────────────
# XML Generation — VAT Returns
# ──────────────────────────────────────────

def generate_vat_xml(report_name, filters, data):
	"""Generate Ministry-compliant VAT declaration XML.

	Args:
		report_name (str): "VAT Sales Register" or "VAT Purchase Register"
		filters (dict): Report filters including company, from_date, to_date
		data (list[dict]): Report result rows

	Returns:
		str: Formatted XML string
	"""
	from frappe.utils import flt

	company = filters.get("company", "")
	# Use cached value to avoid a separate DB round-trip when _run_report
	# already validated and resolved company from the report filters.
	company_tin = frappe.get_cached_value("Company", company, "tax_id") or ""

	root = Element("VATDeclaration")
	root.set("type", "Sales" if "Sales" in report_name else "Purchase")

	# Header section
	header = SubElement(root, "Header")
	SubElement(header, "CompanyTIN").text = cstr(company_tin)
	SubElement(header, "CompanyName").text = cstr(company)
	SubElement(header, "ReportType").text = cstr(report_name)
	SubElement(header, "GeneratedDate").text = cstr(frappe.utils.nowdate())

	# Period
	period = SubElement(root, "Period")
	SubElement(period, "From").text = cstr(filters.get("from_date", ""))
	SubElement(period, "To").text = cstr(filters.get("to_date", ""))

	# Totals
	total_taxable = flt(sum(flt(row.get("taxable_amount", 0)) for row in data), 2)
	total_vat = flt(sum(flt(row.get("vat_amount", 0)) for row in data), 2)
	totals = SubElement(root, "Totals")
	SubElement(totals, "TotalTaxableAmount").text = cstr(total_taxable)
	SubElement(totals, "TotalVATAmount").text = cstr(total_vat)

	# Transactions
	transactions = SubElement(root, "Transactions")
	for row in data:
		txn = SubElement(transactions, "Transaction")
		SubElement(txn, "InvoiceNo").text = cstr(row.get("inv_no", ""))
		SubElement(txn, "Date").text = cstr(row.get("date", ""))
		SubElement(txn, "TaxableAmount").text = cstr(flt(row.get("taxable_amount", 0), 2))
		SubElement(txn, "VATRate").text = cstr(flt(row.get("vat_rate", 0), 2))
		SubElement(txn, "VATAmount").text = cstr(flt(row.get("vat_amount", 0), 2))

		if "Sales" in report_name:
			SubElement(txn, "BuyerTIN").text = cstr(row.get("buyer_tin", ""))
			SubElement(txn, "BuyerName").text = cstr(row.get("buyer_name", ""))
			SubElement(txn, "FSNumber").text = cstr(row.get("mrc", ""))
		else:
			SubElement(txn, "SellerTIN").text = cstr(row.get("seller_tin", ""))
			SubElement(txn, "SellerName").text = cstr(row.get("seller_name", ""))

	# Pretty-print XML
	raw = tostring(root, encoding="unicode")
	dom = minidom.parseString(raw)
	return dom.toprettyxml(indent="  ")


# ──────────────────────────────────────────
# CSV Generation — Darash Format
# ──────────────────────────────────────────

def generate_darash_csv(report_name, filters, data):
	"""Generate Darash-compliant CSV with mapped headers.

	Args:
		report_name (str): Report name
		filters (dict): Report filters
		data (list[dict]): Report result rows

	Returns:
		str: CSV string with Darash-mapped headers
	"""
	if not data:
		return ""

	# Determine which fields to include based on what's present in data
	fieldnames = list(data[0].keys())
	mapped_headers = [DARASH_HEADERS.get(f, f) for f in fieldnames]

	output = io.StringIO()
	writer = csv.writer(output, quoting=csv.QUOTE_ALL)

	# Write mapped header row
	writer.writerow(mapped_headers)

	# Write data rows
	for row in data:
		writer.writerow([cstr(row.get(f, "")) for f in fieldnames])

	return output.getvalue()


# ──────────────────────────────────────────
# Whitelisted Download Endpoints
# ──────────────────────────────────────────

@frappe.whitelist()
def download_vat_xml(report_name, filters=None):
	"""Re-run a VAT report and return XML for download.

	Called from VAT Sales/Purchase Register JS buttons.

	Args:
		report_name (str): "VAT Sales Register" or "VAT Purchase Register"
		filters (dict|str): Report filter values (JSON string if called from JS)
	"""
	frappe.only_for(["Accounts Manager", "System Manager"])

	if isinstance(filters, str):
		import json
		filters = json.loads(filters)

	columns, data = _run_report(report_name, filters)

	if not data:
		frappe.throw(_("No data found for the selected period."))

	xml_content = generate_vat_xml(report_name, filters, data)

	frappe.response['filename'] = "VAT_Return.xml"
	frappe.response['filecontent'] = xml_content
	frappe.response['type'] = 'download'


@frappe.whitelist()
def download_darash_csv(report_name, filters=None):
	"""Re-run a TASS/SIGTAS report and return Darash CSV for download.

	Called from TASS/SIGTAS report JS buttons.

	Args:
		report_name (str): Report name
		filters (dict|str): Report filter values (JSON string if called from JS)
	"""
	frappe.only_for(["Accounts Manager", "System Manager"])

	if isinstance(filters, str):
		import json
		filters = json.loads(filters)

	columns, data = _run_report(report_name, filters)

	if not data:
		frappe.throw(_("No data found for the selected period."))

	csv_content = generate_darash_csv(report_name, filters, data)

	safe_name = report_name.replace(" ", "_")
	frappe.response['filename'] = f"{safe_name}_Darash.csv"
	frappe.response['filecontent'] = csv_content
	frappe.response['type'] = 'download'


# ──────────────────────────────────────────
# Internal: Run a Script Report and return results
# ──────────────────────────────────────────

def _run_report(report_name, filters=None):
	"""Run a Script Report's execute function and return (columns, data).

	Args:
		report_name (str): The report's name as registered in the Report doctype
		filters (dict): Report filter values

	Returns:
		tuple: (columns, data)
	"""
	if filters is None:
		filters = {}

	# Look up the report to find its report_name field
	report_doc = frappe.get_doc("Report", report_name)
	if not report_doc:
		frappe.throw(_("Report {0} not found").format(report_name))

	report_script_name = report_doc.report_name

	# Build the module path for the report's Python file
	# Script reports live in: ethiopia_compliance.report.<snake_case>.py
	# Their execute function is at the module level or inside the module's main file
	report_module_path = _get_report_module_path(report_script_name)
	if not report_module_path:
		frappe.throw(_("Cannot resolve module for report: {0}").format(report_name))

	try:
		mod = __import__(report_module_path, fromlist=["execute"])
		execute_fn = getattr(mod, "execute", None)
		if not execute_fn:
			frappe.throw(_("Report {0} is missing an execute() function").format(report_name))
		return execute_fn(filters)
	except ImportError:
		frappe.throw(_("Cannot import report module: {0}").format(report_module_path))


def _get_report_module_path(report_name):
	"""Map a report's registered name to its Python module path."""
	module_map = {
		"VAT Sales Register": "ethiopia_compliance.report.vat_sales_register.vat_sales_register",
		"VAT Purchase Register": "ethiopia_compliance.report.vat_purchase_register.vat_purchase_register",
		"TASS Sales Declaration": "ethiopia_compliance.report.tass_sales_declaration.tass_sales_declaration",
		"TASS Purchase Declaration": "ethiopia_compliance.report.tass_purchase_declaration.tass_purchase_declaration",
		"TASS Purchase Excel Export": "ethiopia_compliance.report.tass_purchase_excel_export.tass_purchase_excel_export",
		"SIGTAS Withholding Report": "ethiopia_compliance.report.sigtas_withholding_report.sigtas_withholding_report",
	}
	return module_map.get(report_name)
