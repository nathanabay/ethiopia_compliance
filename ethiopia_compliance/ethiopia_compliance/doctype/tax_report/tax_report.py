# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate
import json


class TaxReport(Document):
    def before_save(self):
        """Validate dates before saving"""
        if getdate(self.from_date) > getdate(self.to_date):
            frappe.throw("From Date cannot be greater than To Date")
    
    def on_submit(self):
        """Mark as submitted"""
        self.status = "Submitted"
    
    def on_cancel(self):
        """Mark as cancelled"""
        self.status = "Cancelled"


@frappe.whitelist()
def generate_report(docname):
    """
    Generate tax report based on report type
    """
    doc = frappe.get_doc("Tax Report", docname)
    
    if doc.status == "Submitted":
        frappe.throw("Cannot regenerate a submitted report")
    
    # Generate based on report type
    if doc.report_type == "VAT":
        data = generate_vat_report(doc)
    elif doc.report_type == "WHT":
        data = generate_wht_report(doc)
    elif doc.report_type == "TOT":
        data = generate_tot_report(doc)
    elif doc.report_type == "Excise":
        data = generate_excise_report(doc)
    else:
        frappe.throw(f"Unknown report type: {doc.report_type}")
    
    # Save the generated data
    doc.report_data = json.dumps(data, indent=2, default=str)
    doc.status = "Generated"
    doc.generated_by = frappe.session.user
    doc.generated_on = frappe.utils.now()
    doc.save()
    
    # Generate HTML summary
    doc.report_summary = generate_html_summary(doc.report_type, data)
    doc.save()
    
    frappe.msgprint(f"{doc.report_type} Report generated successfully")
    
    return data


def generate_vat_report(doc):
    """
    Generate VAT report for the period
    """
    # Output VAT (Sales)
    output_vat = frappe.db.sql("""
        SELECT 
            si.name,
            si.posting_date,
            si.customer_name,
            si.base_net_total,
            si.base_total_taxes_and_charges as vat_amount,
            si.grand_total
        FROM `tabSales Invoice` si
        WHERE si.company = %(company)s
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND si.docstatus = 1
        ORDER BY si.posting_date
    """, {'company': doc.company, 'from_date': doc.from_date, 'to_date': doc.to_date}, as_dict=True)
    
    # Input VAT (Purchases)
    input_vat = frappe.db.sql("""
        SELECT 
            pi.name,
            pi.posting_date,
            pi.supplier_name,
            pi.base_net_total,
            pi.base_total_taxes_and_charges as vat_amount,
            pi.grand_total
        FROM `tabPurchase Invoice` pi
        WHERE pi.company = %(company)s
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND pi.docstatus = 1
        ORDER BY pi.posting_date
    """, {'company': doc.company, 'from_date': doc.from_date, 'to_date': doc.to_date}, as_dict=True)
    
    # Calculate totals safely
    total_output_vat = sum(flt(inv.get('vat_amount', 0)) for inv in output_vat)
    total_input_vat = sum(flt(inv.get('vat_amount', 0)) for inv in input_vat)
    net_vat_payable = total_output_vat - total_input_vat
    
    return {
        'report_type': 'VAT',
        'period': f"{doc.from_date} to {doc.to_date}",
        'output_vat': {
            'invoices': output_vat,
            'total': total_output_vat,
            'count': len(output_vat)
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
    """
    Generate WHT (Withholding Tax) report for the period
    """
    wht_data = frappe.db.sql("""
        SELECT 
            pi.name,
            pi.posting_date,
            pi.supplier,
            pi.supplier_name,
            pi.base_net_total,
            pi.base_total_taxes_and_charges as wht_amount,
            pi.grand_total
        FROM `tabPurchase Invoice` pi
        WHERE pi.company = %(company)s
        AND pi.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND pi.docstatus = 1
        AND pi.base_total_taxes_and_charges > 0
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
    """
    Generate TOT (Turnover Tax) report for the period
    """
    # TOT is typically for small businesses as alternative to VAT
    # This is a simplified version
    tot_data = frappe.db.sql("""
        SELECT 
            si.name,
            si.posting_date,
            si.customer_name,
            si.base_net_total,
            si.base_total_taxes_and_charges as tot_amount,
            si.grand_total
        FROM `tabSales Invoice` si
        WHERE si.company = %(company)s
        AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND si.docstatus = 1
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
    """
    Generate Excise Tax report for the period
    """
    # Placeholder for excise tax reporting
    return {
        'report_type': 'Excise',
        'period': f"{doc.from_date} to {doc.to_date}",
        'summary': {
            'message': 'Excise tax reporting will be implemented with excise tax module'
        }
    }


def generate_html_summary(report_type, data):
    """
    Generate HTML summary for display in the form
    """
    if report_type == "VAT":
        return f"""
        <div style="padding: 15px; background: #f8f9fa; border-radius: 5px;">
            <h4>VAT Report Summary</h4>
            <table class="table table-bordered" style="margin-top: 10px;">
                <tr>
                    <td><strong>Total Output VAT (Sales):</strong></td>
                    <td class="text-right">{frappe.format_value(data['summary']['total_output_vat'], {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr>
                    <td><strong>Total Input VAT (Purchases):</strong></td>
                    <td class="text-right">{frappe.format_value(data['summary']['total_input_vat'], {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr style="background: #e7f3ff;">
                    <td><strong>Net VAT Payable:</strong></td>
                    <td class="text-right"><strong>{frappe.format_value(data['summary']['net_vat_payable'], {'fieldtype': 'Currency'})}</strong></td>
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
                    <td class="text-right">{frappe.format_value(data['summary']['total_wht'], {'fieldtype': 'Currency'})}</td>
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
                    <td class="text-right">{frappe.format_value(data['summary']['total_turnover'], {'fieldtype': 'Currency'})}</td>
                </tr>
                <tr>
                    <td><strong>Total TOT:</strong></td>
                    <td class="text-right">{frappe.format_value(data['summary']['total_tot'], {'fieldtype': 'Currency'})}</td>
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


@frappe.whitelist()
def export_to_excel(docname):
    """
    Export tax report to Excel
    """
    try:
        import xlsxwriter
        import io
    except ImportError:
        frappe.throw("xlsxwriter package is required for Excel export. Please install it: pip install xlsxwriter")
    
    doc = frappe.get_doc("Tax Report", docname)
    
    if not doc.report_data:
        frappe.throw("Please generate the report first")
    
    data = json.loads(doc.report_data)
    
    # Create Excel file
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet(f"{doc.report_type} Report")
    
    # Formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'align': 'center'
    })
    currency_format = workbook.add_format({'num_format': '#,##0.00'})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    
    # Write headers
    worksheet.write(0, 0, f"{doc.report_type} Tax Report", header_format)
    worksheet.write(1, 0, f"Period: {doc.from_date} to {doc.to_date}")
    worksheet.write(2, 0, f"Company: {doc.company}")
    
    row = 4
    
    if doc.report_type == "VAT":
        # Output VAT Section
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
        
        # Input VAT Section
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
        # Summary
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
        # WHT Report
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
        # TOT Report
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
    
    # Auto-fit columns
    worksheet.set_column('A:A', 20)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 25)
    worksheet.set_column('D:E', 15)
    
    workbook.close()
    output.seek(0)
    
    frappe.response['filename'] = f"{doc.name}.xlsx"
    frappe.response['filecontent'] = output.read()
    frappe.response['type'] = 'binary'

