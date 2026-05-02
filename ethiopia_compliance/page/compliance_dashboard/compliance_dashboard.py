import frappe
from frappe.utils import today, get_first_day, get_last_day, flt, add_months, add_days
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ethiopia_compliance.utils import get_ec_date


def _get_date_range(period, from_date=None, to_date=None):
	"""Compute date range from period preset or custom dates."""
	period_labels = {
		'this_month': 'This Month',
		'last_month': 'Last Month',
		'last_quarter': 'Last Quarter',
		'this_year': 'This Year',
		'custom': 'Custom'
	}

	today_date = today()

	if period == 'custom' and from_date and to_date:
		return from_date, to_date, 'Custom'

	if period == 'last_month':
		today_dt = datetime.strptime(today_date, '%Y-%m-%d')
		last_month_end = datetime(today_dt.year, today_dt.month, 1) - timedelta(days=1)
		last_month_start = datetime(last_month_end.year, last_month_end.month, 1)
		return (
			last_month_start.strftime('%Y-%m-%d'),
			last_month_end.strftime('%Y-%m-%d'),
			period_labels[period]
		)

	if period == 'last_quarter':
		today_dt = datetime.strptime(today_date, '%Y-%m-%d')
		quarter_start_month = ((today_dt.month - 1) // 3) * 3 + 1
		quarter_start = datetime(today_dt.year, quarter_start_month, 1)
		prev_quarter_end = quarter_start - timedelta(days=1)
		prev_quarter_start = datetime(prev_quarter_end.year, ((prev_quarter_end.month - 1) // 3) * 3 + 1, 1)
		return (
			prev_quarter_start.strftime('%Y-%m-%d'),
			prev_quarter_end.strftime('%Y-%m-%d'),
			period_labels[period]
		)

	if period == 'this_year':
		today_dt = datetime.strptime(today_date, '%Y-%m-%d')
		year_start = datetime(today_dt.year, 1, 1)
		return (
			year_start.strftime('%Y-%m-%d'),
			today_date,
			period_labels[period]
		)

	# Default: this_month
	return (
		get_first_day(today_date),
		get_last_day(today_date),
		period_labels['this_month']
	)


@frappe.whitelist(methods=["GET", "POST"], xss_safe=True)
def get_dashboard_data(period='this_month', from_date=None, to_date=None) -> dict:
	"""Get all data for compliance dashboard (restricted to Accounts roles)"""
	frappe.only_for(["Accounts Manager", "Accounts User", "System Manager"])

	company = frappe.defaults.get_user_default("Company")
	if not company:
		return {}

	today_date = today()
	month_start, month_end, period_label = _get_date_range(period, from_date, to_date)
	ethiopian_today = get_ec_date(today_date)

	return {
		'tax_summary': get_tax_summary(company, month_start, month_end),
		'ethiopian_date': ethiopian_today,
		'gregorian_date': today_date,
		'recent_documents': get_recent_documents(company, month_start, month_end),
		'compliance_status': get_compliance_status(company),
		'month_start': month_start,
		'month_end': month_end,
		'period_label': _(period_label),
		'period': period,
		'company': company
	}


def get_tax_summary(company, from_date, to_date):
	"""Get tax summary for the period with 1-hour caching"""
	cache_key = f"ethiopia_compliance:tax_summary:{company}:{from_date}:{to_date}"
	cached = frappe.cache().get_value(cache_key)
	if cached is not None:
		return cached

	def _fetch():
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

		# TOT Summary - uses configured TOT account from Compliance Setting
		tot_data = None
		try:
			settings = frappe.get_cached_doc("Compliance Setting")
			if settings.get("tot_account"):
				tot_account = settings.tot_account
				tot_data = frappe.db.sql("""
					SELECT
						SUM(si.base_net_total) as total_turnover,
						ABS(SUM(stc.tax_amount)) as total_tot
					FROM `tabSales Invoice` si
					JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
					WHERE si.company = %s
					AND si.posting_date BETWEEN %s AND %s
					AND si.docstatus = 1
					AND stc.account_head = %s
				""", (company, from_date, to_date, tot_account), as_dict=True)
		except Exception:
			pass

		return {
			'wht': {
				'total_purchases': flt(wht_data[0].total_purchases) if wht_data and wht_data[0].total_purchases else 0,
				'total_wht': flt(wht_data[0].total_wht) if wht_data and wht_data[0].total_wht else 0
			},
			'vat': {
				'total_sales': flt(vat_data[0].total_sales) if vat_data and vat_data[0].total_sales else 0,
				'total_vat': flt(vat_data[0].total_vat) if vat_data and vat_data[0].total_vat else 0
			},
			'tot': {
				'total_turnover': flt(tot_data[0].total_turnover) if tot_data and tot_data[0].total_turnover else 0,
				'total_tot': flt(tot_data[0].total_tot) if tot_data and tot_data[0].total_tot else 0
			}
		}

	result = _fetch()
	frappe.cache().set_value(cache_key, result, expires_in_sec=3600)
	return result


def get_recent_documents(company, from_date=None, to_date=None, limit=10):
	"""Get recent tax-relevant documents within date range"""
	documents = []

	filters = {'company': company, 'docstatus': 1}
	if from_date and to_date:
		filters['posting_date'] = ['between', [from_date, to_date]]

	sales_invoices = frappe.get_all('Sales Invoice',
		filters=filters,
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
		filters=filters,
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
