import frappe
from frappe.utils import today, get_first_day, get_last_day, flt
from frappe import _
from ethiopia_compliance.utils import get_ec_date


@frappe.whitelist(methods=["GET"], xss_safe=True)
def get_dashboard_data() -> dict:
	"""Get all data for compliance dashboard (restricted to Accounts roles)"""
	frappe.only_for(["Accounts Manager", "Accounts User", "System Manager"])

	company = frappe.defaults.get_user_default("Company")
	if not company:
		return {}

	today_date = today()
	month_start = get_first_day(today_date)
	month_end = get_last_day(today_date)
	ethiopian_today = get_ec_date(today_date)

	return {
		'tax_summary': get_tax_summary(company, month_start, month_end),
		'ethiopian_date': ethiopian_today,
		'gregorian_date': today_date,
		'recent_documents': get_recent_documents(company),
		'compliance_status': get_compliance_status(company),
		'month_start': month_start,
		'month_end': month_end
	}


def get_tax_summary(company, from_date, to_date):
	"""Get tax summary for the period"""
	# WHT Summary - join tax table for accurate WHT amounts
	wht_data = frappe.db.sql("""
		SELECT
			SUM(pi.base_net_total) as total_purchases,
			ABS(SUM(ptc.tax_amount)) as total_wht
		FROM `tabPurchase Invoice` pi
		JOIN `tabPurchase Taxes and Charges` ptc ON ptc.parent = pi.name
		WHERE pi.company = %s
		AND pi.posting_date BETWEEN %s AND %s
		AND pi.docstatus = 1
		AND (ptc.account_head LIKE '%%Withholding%%' OR ptc.description LIKE '%%WHT%%')
	""", (company, from_date, to_date), as_dict=True)

	# VAT Summary - join tax table for accurate VAT amounts
	vat_data = frappe.db.sql("""
		SELECT
			SUM(si.base_net_total) as total_sales,
			ABS(SUM(stc.tax_amount)) as total_vat
		FROM `tabSales Invoice` si
		JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
		WHERE si.company = %s
		AND si.posting_date BETWEEN %s AND %s
		AND si.docstatus = 1
		AND (stc.account_head LIKE '%%VAT%%' OR stc.description LIKE '%%VAT%%')
	""", (company, from_date, to_date), as_dict=True)

	return {
		'wht': {
			'total_purchases': flt(wht_data[0].total_purchases) if wht_data and wht_data[0].total_purchases else 0,
			'total_wht': flt(wht_data[0].total_wht) if wht_data and wht_data[0].total_wht else 0
		},
		'vat': {
			'total_sales': flt(vat_data[0].total_sales) if vat_data and vat_data[0].total_sales else 0,
			'total_vat': flt(vat_data[0].total_vat) if vat_data and vat_data[0].total_vat else 0
		}
	}


def get_recent_documents(company, limit=10):
	"""Get recent tax-relevant documents"""
	documents = []

	sales_invoices = frappe.get_all('Sales Invoice',
		filters={'company': company, 'docstatus': 1},
		fields=['name', 'posting_date', 'customer', 'grand_total'],
		order_by='posting_date desc',
		limit=limit)

	for inv in sales_invoices:
		documents.append({
			'type': 'Sales Invoice',
			'name': inv.name,
			'date': inv.posting_date,
			'party': inv.customer,
			'amount': inv.grand_total
		})

	purchase_invoices = frappe.get_all('Purchase Invoice',
		filters={'company': company, 'docstatus': 1},
		fields=['name', 'posting_date', 'supplier', 'grand_total'],
		order_by='posting_date desc',
		limit=limit)

	for inv in purchase_invoices:
		documents.append({
			'type': 'Purchase Invoice',
			'name': inv.name,
			'date': inv.posting_date,
			'party': inv.supplier,
			'amount': inv.grand_total
		})

	documents.sort(key=lambda x: x['date'], reverse=True)
	return documents[:limit]


def get_compliance_status(company):
	"""Check compliance status"""
	status = {
		'settings_configured': False,
		'calendar_enabled': False,
		'fiscal_year_set': False
	}

	try:
		settings = frappe.get_cached_doc("Compliance Setting")
		if settings.wht_rate and settings.vat_rate:
			status['settings_configured'] = True
		if settings.enable_ethiopian_calendar:
			status['calendar_enabled'] = True
	except Exception:
		pass

	if frappe.db.exists('Fiscal Year', '2017 E.C.'):
		status['fiscal_year_set'] = True

	return status
