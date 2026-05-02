# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate
from frappe import _
import json


class TaxReport(Document):
	def validate(self):
		"""Validate dates and status transitions"""
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be greater than To Date"))

		if not self.is_new():
			valid_transitions = {
				"Draft": ["Generated"],
				"Generated": ["Submitted", "Draft"],
				"Submitted": ["Cancelled"],
			}
			old_status = self.get_db_value("status")
			if old_status and old_status != self.status:
				allowed = valid_transitions.get(old_status, [])
				if self.status not in allowed:
					frappe.throw(_("Invalid status transition from {0} to {1}").format(
						old_status, self.status))

	def on_submit(self):
		"""Mark as submitted"""
		self.db_set("status", "Submitted")

	def on_cancel(self):
		"""Mark as cancelled"""
		self.db_set("status", "Cancelled")


@frappe.whitelist(methods=["POST"], xss_safe=True)
def generate_report(docname: str) -> str:
	"""Queue report generation as a background job"""
	docname = str(docname)
	doc = frappe.get_doc("Tax Report", docname)

	if not doc.has_permission("write"):
		raise frappe.PermissionError(_("You do not have permission to modify this report"))

	if doc.status == "Submitted":
		frappe.throw(_("Cannot regenerate a submitted report"))

	if doc.status == "Generating":
		frappe.throw(_("Report is already being generated. Please wait."))

	# Mark as generating immediately
	doc.db_set("status", "Generating")

	frappe.enqueue(
		"ethiopia_compliance.ethiopia_compliance.doctype.tax_report.tax_report._generate_report_async",
		queue="long",
		timeout=600,
		docname=docname,
		user=frappe.session.user,
	)

	return "Report generation started. Please refresh in a few moments."


def _generate_report_async(docname, user=None):
	"""Background worker: generates the actual report data"""
	if user:
		frappe.set_user(user)

	doc = frappe.get_doc("Tax Report", docname)

	try:
		if doc.report_type == "VAT":
			data = generate_vat_report(doc)
		elif doc.report_type == "WHT":
			data = generate_wht_report(doc)
		elif doc.report_type == "TOT":
			data = generate_tot_report(doc)
		elif doc.report_type == "Excise":
			data = generate_excise_report(doc)
		else:
			frappe.throw(_("Unknown report type: {0}").format(doc.report_type))

		doc.report_data = json.dumps(data, indent=2, default=str)
		doc.report_summary = generate_html_summary(doc.report_type, data)
		doc.status = "Generated"
		doc.generated_by = user or frappe.session.user
		doc.generated_on = frappe.utils.now()
		doc.save()

	except Exception:
		doc.db_set("status", "Draft")
		frappe.log_error(title=f"Tax Report Generation Failed: {docname}")
		raise


def generate_vat_report(doc):
	"""Generate VAT report for the period"""
	output_vat = frappe.db.sql("""
		SELECT
			si.name, si.posting_date, si.customer_name,
			si.base_net_total, si.grand_total
		FROM `tabSales Invoice` si
		WHERE si.company = %(company)s
		AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND si.docstatus = 1
		ORDER BY si.posting_date
	""", {'company': doc.company, 'from_date': doc.from_date, 'to_date': doc.to_date}, as_dict=True)

	# Get VAT amounts from tax table
	vat_invoices = frappe.db.sql("""
		SELECT
			si.name, si.posting_date, si.customer_name,
			si.base_net_total, ABS(stc.tax_amount) as vat_amount, si.grand_total
		FROM `tabSales Invoice` si
		JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
		WHERE si.company = %(company)s
		AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND si.docstatus = 1
		AND stc.account_head LIKE %(vat_account)s
		ORDER BY si.posting_date
	""", {
		'company': doc.company,
		'from_date': doc.from_date,
		'to_date': doc.to_date,
		'vat_account': '%VAT%'
	}, as_dict=True)

	input_vat = frappe.db.sql("""
		SELECT
			pi.name, pi.posting_date, pi.supplier_name,
			pi.base_net_total, ABS(ptc.tax_amount) as vat_amount, pi.grand_total
		FROM `tabPurchase Invoice` pi
		JOIN `tabPurchase Taxes and Charges` ptc ON ptc.parent = pi.name
		WHERE pi.company = %(company)s
		AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND pi.docstatus = 1
		AND ptc.account_head LIKE %(vat_account)s
		ORDER BY pi.posting_date
	""", {
		'company': doc.company,
		'from_date': doc.from_date,
		'to_date': doc.to_date,
		'vat_account': '%VAT%'
	}, as_dict=True)

	total_output_vat = sum(flt(inv.get('vat_amount', 0)) for inv in vat_invoices)
	total_input_vat = sum(flt(inv.get('vat_amount', 0)) for inv in input_vat)
	net_vat_payable = total_output_vat - total_input_vat

	return {
		'report_type': 'VAT',
		'period': f"{doc.from_date} to {doc.to_date}",
		'output_vat': {
			'invoices': vat_invoices,
			'total': total_output_vat,
			'count': len(vat_invoices)
		},
		'input_vat': {
			'invoices': input_vat,
			'total': total_input_vat,
			'count': len(input_vat)
		},
		'summary': {
			'total_output_vat': total_output_vat,
			'total_input_vat': total_input_vat,
			'net_vat_payable': net_vat_payable
		}
	}


def generate_wht_report(doc):
	"""Generate WHT (Withholding Tax) report for the period"""
	wht_data = frappe.db.sql("""
		SELECT
			pi.name, pi.posting_date, pi.supplier, pi.supplier_name,
			pi.base_net_total, ABS(ptc.tax_amount) as wht_amount, pi.grand_total
		FROM `tabPurchase Invoice` pi
		JOIN `tabPurchase Taxes and Charges` ptc ON ptc.parent = pi.name
		WHERE pi.company = %(company)s
		AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND pi.docstatus = 1
		AND (ptc.account_head LIKE '%%Withholding%%' OR ptc.description LIKE '%%WHT%%')
		ORDER BY pi.posting_date, pi.supplier
	""", {'company': doc.company, 'from_date': doc.from_date, 'to_date': doc.to_date}, as_dict=True)

	# Group by supplier
	supplier_summary = {}
	for inv in wht_data:
		supplier_id = inv.get('supplier', '')
		if supplier_id not in supplier_summary:
			supplier_summary[supplier_id] = {
				'supplier_name': inv.get('supplier_name', ''),
				'total_purchases': 0,
				'total_wht': 0,
				'invoice_count': 0
			}
		supplier_summary[supplier_id]['total_purchases'] += flt(inv.get('base_net_total', 0))
		supplier_summary[supplier_id]['total_wht'] += flt(inv.get('wht_amount', 0))
		supplier_summary[supplier_id]['invoice_count'] += 1

	total_wht = sum(flt(inv.get('wht_amount', 0)) for inv in wht_data)

	return {
		'report_type': 'WHT',
		'period': f"{doc.from_date} to {doc.to_date}",
		'invoices': wht_data,
		'supplier_summary': supplier_summary,
		'summary': {
			'total_invoices': len(wht_data),
			'total_suppliers': len(supplier_summary),
			'total_wht': total_wht
		}
	}


def generate_tot_report(doc):
	"""Generate TOT (Turnover Tax) report for the period"""
	tot_data = frappe.db.sql("""
		SELECT
			si.name, si.posting_date, si.customer_name,
			si.base_net_total, ABS(stc.tax_amount) as tot_amount, si.grand_total
		FROM `tabSales Invoice` si
		JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
		WHERE si.company = %(company)s
		AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
		AND si.docstatus = 1
		AND (stc.account_head LIKE '%%TOT%%' OR stc.description LIKE '%%TOT%%')
		ORDER BY si.posting_date
	""", {'company': doc.company, 'from_date': doc.from_date, 'to_date': doc.to_date}, as_dict=True)

	total_turnover = sum(flt(inv.get('base_net_total', 0)) for inv in tot_data)
	total_tot = sum(flt(inv.get('tot_amount', 0)) for inv in tot_data)

	return {
		'report_type': 'TOT',
		'period': f"{doc.from_date} to {doc.to_date}",
		'invoices': tot_data,
		'summary': {
			'total_turnover': total_turnover,
			'total_tot': total_tot,
			'invoice_count': len(tot_data)
		}
	}


def generate_excise_report(doc):
	"""Generate Excise Tax report for the period"""
	return {
		'report_type': 'Excise',
		'period': f"{doc.from_date} to {doc.to_date}",
		'summary': {
			'message': 'Excise tax reporting will be implemented with excise tax module'
		}
	}


def generate_html_summary(report_type, data):
	"""Generate HTML summary for display in the form"""
	if report_type == "VAT":
		return f"""
		<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">
			<h4>VAT Report Summary</h4>
			<table class="table table-bordered" style="margin-top: 10px;">
				<tr>
					<td><strong>Total Output VAT (Sales):</strong></td>
					<td class="text-right">{frappe.format_value(data['summary']['total_output_vat'], {{'fieldtype': 'Currency'}})}</td>
				</tr>
				<tr>
					<td><strong>Total Input VAT (Purchases):</strong></td>
					<td class="text-right">{frappe.format_value(data['summary']['total_input_vat'], {{'fieldtype': 'Currency'}})}</td>
				</tr>
				<tr style="background: #e7f3ff;">
					<td><strong>Net VAT Payable:</strong></td>
					<td class="text-right"><strong>{frappe.format_value(data['summary']['net_vat_payable'], {{'fieldtype': 'Currency'}})}</strong></td>
				</tr>
			</table>
			<p class="text-muted">Sales Invoices: {data['output_vat']['count']} | Purchase Invoices: {data['input_vat']['count']}</p>
		</div>
		"""
	elif report_type == "WHT":
		return f"""
		<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">
			<h4>WHT Report Summary</h4>
			<table class="table table-bordered" style="margin-top: 10px;">
				<tr>
					<td><strong>Total WHT Deducted:</strong></td>
					<td class="text-right">{frappe.format_value(data['summary']['total_wht'], {{'fieldtype': 'Currency'}})}</td>
				</tr>
				<tr>
					<td><strong>Total Suppliers:</strong></td>
					<td class="text-right">{data['summary']['total_suppliers']}</td>
				</tr>
				<tr>
					<td><strong>Total Invoices:</strong></td>
					<td class="text-right">{data['summary']['total_invoices']}</td>
				</tr>
			</table>
		</div>
		"""
	elif report_type == "TOT":
		return f"""
		<div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">
			<h4>TOT Report Summary</h4>
			<table class="table table-bordered" style="margin-top: 10px;">
				<tr>
					<td><strong>Total Turnover:</strong></td>
					<td class="text-right">{frappe.format_value(data['summary']['total_turnover'], {{'fieldtype': 'Currency'}})}</td>
				</tr>
				<tr>
					<td><strong>Total TOT:</strong></td>
					<td class="text-right">{frappe.format_value(data['summary']['total_tot'], {{'fieldtype': 'Currency'}})}</td>
				</tr>
				<tr>
					<td><strong>Invoice Count:</strong></td>
					<td class="text-right">{data['summary']['invoice_count']}</td>
				</tr>
			</table>
		</div>
		"""
	else:
		return "<p>Report summary not available</p>"


@frappe.whitelist(methods=["GET", "POST"], xss_safe=True)
def export_to_excel(docname: str):
	"""Export tax report to Excel"""
	docname = str(docname)
	doc = frappe.get_doc("Tax Report", docname)

	if not doc.has_permission("read"):
		raise frappe.PermissionError(_("You do not have permission to export this report"))

	if not doc.report_data:
		frappe.throw(_("Please generate the report first"))

	try:
		import xlsxwriter
		import io
	except ImportError:
		frappe.throw(_("xlsxwriter package is required. Install with: pip install xlsxwriter"))

	data = json.loads(doc.report_data)

	output = io.BytesIO()
	workbook = xlsxwriter.Workbook(output, {'in_memory': True})
	worksheet = workbook.add_worksheet(f"{doc.report_type} Report")

	header_format = workbook.add_format({
		'bold': True,
		'bg_color': '#4472C4',
		'font_color': 'white',
		'align': 'center'
	})
	currency_format = workbook.add_format({'num_format': '#,##0.00'})

	worksheet.write(0, 0, f"{doc.report_type} Tax Report", header_format)
	worksheet.write(1, 0, f"Period: {doc.from_date} to {doc.to_date}")
	worksheet.write(2, 0, f"Company: {doc.company}")

	row = 4

	if doc.report_type == "VAT":
		worksheet.write(row, 0, "OUTPUT VAT (Sales)", header_format)
		worksheet.write(row, 1, "Date", header_format)
		worksheet.write(row, 2, "Customer", header_format)
		worksheet.write(row, 3, "Net Total", header_format)
		worksheet.write(row, 4, "VAT Amount", header_format)
		row += 1

		for inv in data.get('output_vat', {}).get('invoices', []):
			worksheet.write(row, 0, inv.get('name', ''))
			worksheet.write(row, 1, str(inv.get('posting_date', '')))
			worksheet.write(row, 2, inv.get('customer_name', ''))
			worksheet.write(row, 3, flt(inv.get('base_net_total', 0)), currency_format)
			worksheet.write(row, 4, flt(inv.get('vat_amount', 0)), currency_format)
			row += 1

		row += 1
		worksheet.write(row, 0, "INPUT VAT (Purchases)", header_format)
		worksheet.write(row, 1, "Date", header_format)
		worksheet.write(row, 2, "Supplier", header_format)
		worksheet.write(row, 3, "Net Total", header_format)
		worksheet.write(row, 4, "VAT Amount", header_format)
		row += 1

		for inv in data.get('input_vat', {}).get('invoices', []):
			worksheet.write(row, 0, inv.get('name', ''))
			worksheet.write(row, 1, str(inv.get('posting_date', '')))
			worksheet.write(row, 2, inv.get('supplier_name', ''))
			worksheet.write(row, 3, flt(inv.get('base_net_total', 0)), currency_format)
			worksheet.write(row, 4, flt(inv.get('vat_amount', 0)), currency_format)
			row += 1

		row += 2
		summary = data.get('summary', {})
		worksheet.write(row, 0, "Total Output VAT:")
		worksheet.write(row, 1, flt(summary.get('total_output_vat', 0)), currency_format)
		row += 1
		worksheet.write(row, 0, "Total Input VAT:")
		worksheet.write(row, 1, flt(summary.get('total_input_vat', 0)), currency_format)
		row += 1
		worksheet.write(row, 0, "Net VAT Payable:")
		worksheet.write(row, 1, flt(summary.get('net_vat_payable', 0)), currency_format)

	elif doc.report_type == "WHT":
		worksheet.write(row, 0, "Invoice", header_format)
		worksheet.write(row, 1, "Date", header_format)
		worksheet.write(row, 2, "Supplier", header_format)
		worksheet.write(row, 3, "Net Total", header_format)
		worksheet.write(row, 4, "WHT Amount", header_format)
		row += 1

		for inv in data.get('invoices', []):
			worksheet.write(row, 0, inv.get('name', ''))
			worksheet.write(row, 1, str(inv.get('posting_date', '')))
			worksheet.write(row, 2, inv.get('supplier_name', ''))
			worksheet.write(row, 3, flt(inv.get('base_net_total', 0)), currency_format)
			worksheet.write(row, 4, flt(inv.get('wht_amount', 0)), currency_format)
			row += 1

		row += 2
		summary = data.get('summary', {})
		worksheet.write(row, 0, "Total WHT Deducted:")
		worksheet.write(row, 1, flt(summary.get('total_wht', 0)), currency_format)

	elif doc.report_type == "TOT":
		worksheet.write(row, 0, "Invoice", header_format)
		worksheet.write(row, 1, "Date", header_format)
		worksheet.write(row, 2, "Customer", header_format)
		worksheet.write(row, 3, "Turnover", header_format)
		worksheet.write(row, 4, "TOT Amount", header_format)
		row += 1

		for inv in data.get('invoices', []):
			worksheet.write(row, 0, inv.get('name', ''))
			worksheet.write(row, 1, str(inv.get('posting_date', '')))
			worksheet.write(row, 2, inv.get('customer_name', ''))
			worksheet.write(row, 3, flt(inv.get('base_net_total', 0)), currency_format)
			worksheet.write(row, 4, flt(inv.get('tot_amount', 0)), currency_format)
			row += 1

		row += 2
		summary = data.get('summary', {})
		worksheet.write(row, 0, "Total Turnover:")
		worksheet.write(row, 1, flt(summary.get('total_turnover', 0)), currency_format)
		row += 1
		worksheet.write(row, 0, "Total TOT:")
		worksheet.write(row, 1, flt(summary.get('total_tot', 0)), currency_format)

	worksheet.set_column('A:A', 20)
	worksheet.set_column('B:B', 15)
	worksheet.set_column('C:C', 25)
	worksheet.set_column('D:E', 15)

	workbook.close()
	output.seek(0)

	frappe.response['filename'] = f"{doc.name}.xlsx"
	frappe.response['filecontent'] = output.read()
	frappe.response['type'] = 'binary'
