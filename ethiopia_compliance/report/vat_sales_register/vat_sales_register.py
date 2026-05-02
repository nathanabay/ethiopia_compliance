# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from ethiopia_compliance.utils import get_gc_date

def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "seller_tin", "label": _("Seller TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_tin", "label": _("Buyer TIN"), "fieldtype": "Data", "width": 140},
		{"fieldname": "buyer_name", "label": _("Buyer Name"), "fieldtype": "Data", "width": 180},
		{"fieldname": "inv_no", "label": _("Invoice No"), "fieldtype": "Data", "width": 160},
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 100},
		{"fieldname": "taxable_amount", "label": _("Taxable Amount"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "vat_rate", "label": _("VAT Rate"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "vat_amount", "label": _("VAT Amount"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "mrc", "label": _("MRC (Machine Code)"), "fieldtype": "Data", "width": 140}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

	# Ethiopian Calendar date conversion
	if filters.get("use_ethiopian_calendar"):
		if filters.get("from_date"):
			parts = str(filters["from_date"]).split("-")
			if len(parts) == 3:
				eth_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
				gc_date = get_gc_date(eth_date)
				if gc_date:
					filters["from_date"] = gc_date
		if filters.get("to_date"):
			parts = str(filters["to_date"]).split("-")
			if len(parts) == 3:
				eth_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
				gc_date = get_gc_date(eth_date)
				if gc_date:
					filters["to_date"] = gc_date

	conditions = ["s.docstatus = 1"]
	values = {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"],
		"vat_account": "%%VAT%%"
	}

	conditions.append("s.company = %(company)s")
	conditions.append("s.posting_date >= %(from_date)s")
	conditions.append("s.posting_date <= %(to_date)s")

	data = frappe.db.sql("""
		SELECT
			c.tax_id as seller_tin,
			cust.tax_id as buyer_tin,
			s.customer_name as buyer_name,
			s.name as inv_no,
			s.posting_date as date,
			s.net_total as taxable_amount,
			tc.rate as vat_rate,
			tc.tax_amount as vat_amount,
			s.custom_fiscal_machine_no as mrc
		FROM `tabSales Invoice` s
		JOIN `tabSales Taxes and Charges` tc ON tc.parent = s.name
		JOIN `tabCompany` c ON s.company = c.name
		LEFT JOIN `tabCustomer` cust ON s.customer = cust.name
		WHERE tc.account_head LIKE %(vat_account)s
			AND {where}
		ORDER BY s.posting_date, s.name
	""".format(where=" AND ".join(conditions)), values, as_dict=True)

	return columns, data
