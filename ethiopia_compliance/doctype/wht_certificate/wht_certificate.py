# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class WHTCertificate(Document):
	def before_save(self):
		"""Validate dates and generate certificate data"""
		if self.period_from and self.period_to:
			if frappe.utils.getdate(self.period_from) > frappe.utils.getdate(self.period_to):
				frappe.throw(_("Period From cannot be after Period To"))
	
	def before_submit(self):
		"""Generate certificate data before submission"""
		self.generate_certificate_data()
	
	def on_submit(self):
		"""Mark as issued"""
		self.db_set({
			"status": "Issued",
			"issued_by": frappe.session.user,
			"issued_on": frappe.utils.now()
		})

	def on_cancel(self):
		"""Mark as cancelled"""
		self.db_set("status", "Cancelled")
	
	@frappe.whitelist()
	def generate_certificate_data(self):
		"""Fetch purchase invoices and calculate WHT"""
		# Get all submitted purchase invoices for the supplier in the period
		invoices = frappe.db.sql("""
			SELECT 
				pi.name,
				pi.posting_date,
				pi.base_net_total,
				(SELECT SUM(tax_amount) FROM `tabPurchase Taxes and Charges` 
				 WHERE parent = pi.name AND (account_head LIKE '%%Withholding%%' OR description LIKE '%%WHT%%')) as wht_amount,
				pi.grand_total
			FROM `tabPurchase Invoice` pi
			WHERE pi.supplier = %(supplier)s
			AND pi.company = %(company)s
			AND pi.posting_date BETWEEN %(period_from)s AND %(period_to)s
			AND pi.docstatus = 1
			HAVING wht_amount > 0
			ORDER BY pi.posting_date
		""", {
			'supplier': self.supplier,
			'company': self.company,
			'period_from': self.period_from,
			'period_to': self.period_to
		}, as_dict=True)
		
		# Clear existing details
		self.invoice_details = []
		
		total_purchase = 0
		total_wht = 0
		
		# Add invoice details
		for inv in invoices:
			self.append('invoice_details', {
				'invoice': inv.get('name'),
				'posting_date': inv.get('posting_date'),
				'purchase_amount': flt(inv.get('base_net_total', 0)),
				'wht_deducted': flt(inv.get('wht_amount', 0))
			})
			total_purchase += flt(inv.get('base_net_total', 0))
			total_wht += flt(inv.get('wht_amount', 0))
		
		# Update totals
		self.total_purchase_amount = total_purchase
		self.total_wht_deducted = total_wht
		
		# Calculate average WHT rate
		if total_purchase > 0:
			self.wht_rate = flt((total_wht / total_purchase) * 100, 2)


@frappe.whitelist(force_types=True)
def generate_certificate(supplier: str, company: str, period_from: str,
                         period_to: str, fiscal_year: str | None = None) -> dict:
	"""API to generate WHT certificate."""
	frappe.only_for(["Accounts Manager", "System Manager"])
	# Check if certificate already exists
	existing = frappe.db.exists("WHT Certificate", {
		"supplier": supplier,
		"company": company,
		"period_from": period_from,
		"period_to": period_to,
		"docstatus": ["<", 2]
	})
	
	if existing:
		return frappe.get_doc("WHT Certificate", existing)
	
	# Create new certificate
	cert = frappe.new_doc("WHT Certificate")
	cert.supplier = supplier
	cert.company = company
	cert.period_from = period_from
	cert.period_to = period_to
	cert.fiscal_year = fiscal_year
	cert.generate_certificate_data()
	cert.save()
	
	return cert
