import frappe
from frappe.utils import today, get_first_day, get_last_day, flt, add_months, add_days
from frappe import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from ethiopia_compliance.utils import get_ec_date
from ethiopia_compliance.tasks.compliance_alerts import get_tax_calendar


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
		'tax_calendar': get_tax_calendar(),
		'month_start': month_start,
		'month_end': month_end,
		'period_label': _(period_label),
		'period': period,
		'company': company,
		'overview_stats': get_overview_stats(company),
		'chart_data': get_chart_data(period, month_start, month_end)
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
		tot_configured = False
		try:
			settings = frappe.get_cached_doc("Compliance Setting")
			if settings.get("tot_account"):
				tot_account = settings.tot_account
				tot_configured = True
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
			},
			'tot_configured': tot_configured
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


def get_overview_stats(company=None):
    """Get overview statistics for dashboard stat cards"""
    if not company:
        company = frappe.defaults.get_user_default("Company")

    if not company:
        return {
            'total_companies': 0,
            'fiscal_devices': 0,
            'employees': 0,
            'active_contracts': 0
        }

    # Count companies in Ethiopia
    total_companies = frappe.db.count("Company", {"country": "Ethiopia"})

    # Count active fiscal devices (gracefully handle if doctype doesn't exist)
    try:
        fiscal_devices = frappe.db.count("Fiscal Device", {"status": "Active"})
    except Exception:
        fiscal_devices = 0

    # Count employees for this company
    try:
        employees = frappe.db.count("Employee", {"company": company, "status": "Active"})
    except Exception:
        employees = 0

    # Count active contracts (gracefully handle if doctype doesn't exist)
    try:
        active_contracts = frappe.db.count("Contract", {"status": "Active", "company": company})
    except Exception:
        active_contracts = 0

    return {
        'total_companies': total_companies,
        'fiscal_devices': fiscal_devices,
        'employees': employees,
        'active_contracts': active_contracts
    }


def get_chart_data(period='this_month', from_date=None, to_date=None):
    """Get chart data for the dashboard - Revenue, Expenses, Cash Flow, Taxes"""
    from frappe.utils import add_months, get_last_day
    from datetime import datetime

    company = frappe.defaults.get_user_default("Company")

    if not company:
        return {"revenue": [], "expenses": [], "cash_flow": [], "taxes": {"wht": [], "vat": [], "tot": []}}

    # Respect the period parameter using _get_date_range
    month_start, month_end, period_label = _get_date_range(period, from_date, to_date)

    # Cache key based on company and date range
    cache_key = f"ethiopia_compliance:chart_data:{company}:{month_start}:{month_end}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return cached

    # Validate/whitelist allowed doctypes, date fields, and amount fields
    allowed_doctypes = {"Sales Invoice", "Purchase Invoice"}
    allowed_date_fields = {"posting_date", "creation"}
    allowed_amount_fields = {"base_net_total", "grand_total", "rounded_total"}

    def validate_field(value, allowed_set, field_name):
        if value not in allowed_set:
            frappe.throw(_(f"Invalid {field_name}: {value}"))
        return value

    # Determine months to query based on the date range
    # Build list of (month_start, month_end, label) tuples for each month in range
    months_ordered = []
    months_query_params = []

    # Parse month_start and month_end to determine the range
    start_dt = datetime.strptime(month_start, '%Y-%m-%d')
    end_dt = datetime.strptime(month_end, '%Y-%m-%d')

    # Generate all months from month_start to month_end (inclusive)
    current_dt = start_dt
    while current_dt <= end_dt:
        month_label = current_dt.strftime('%b')
        month_end_of = get_last_day(current_dt.strftime('%Y-%m-%d'))
        months_ordered.append(month_label)
        months_query_params.append((current_dt.strftime('%Y-%m-%d'), month_end_of.strftime('%Y-%m-%d'), company))
        # Move to next month
        if current_dt.month == 12:
            current_dt = datetime(current_dt.year + 1, 1, 1)
        else:
            current_dt = datetime(current_dt.year, current_dt.month + 1, 1)

    # Get monthly data for revenue and expenses
    def get_monthly_data(doctype, date_field, amount_field="base_net_total"):
        # Validate inputs to prevent SQL injection
        safe_doctype = validate_field(doctype, allowed_doctypes, "doctype")
        safe_date_field = validate_field(date_field, allowed_date_fields, "date_field")
        safe_amount_field = validate_field(amount_field, allowed_amount_fields, "amount_field")

        months_data = {}
        for params in months_query_params:
            month_date, month_end_dt, _ = params

            data = frappe.db.sql(f"""
                SELECT SUM({safe_amount_field}) as amount
                FROM `tab{safe_doctype}`
                WHERE {safe_date_field} BETWEEN %s AND %s
                AND company = %s
                AND docstatus = 1
            """, (month_date, month_end_dt, company), as_dict=True)

            month_dt = datetime.strptime(month_date, '%Y-%m-%d')
            month_label = month_dt.strftime('%b')
            months_data[month_label] = flt(data[0].amount) if data and data[0].amount else 0

        # Return in chronological order (oldest to newest)
        return [{"month": label, "amount": months_data.get(label, 0)} for label in months_ordered]

    revenue = get_monthly_data("Sales Invoice", "posting_date")
    expenses = get_monthly_data("Purchase Invoice", "posting_date")

    # Cash flow = revenue - expenses per month
    cash_flow = []
    for rev, exp in zip(revenue, expenses):
        cash_flow.append({"month": rev["month"], "amount": rev["amount"] - exp["amount"]})

    # Consolidated tax query for all months in the date range

    # Build consolidated WHT query
    wht_query = """
        SELECT
            pi.posting_date,
            ABS(SUM(ptc.tax_amount)) as amount
        FROM `tabPurchase Invoice` pi
        JOIN `tabPurchase Taxes and Charges` ptc ON ptc.parent = pi.name
        WHERE pi.posting_date BETWEEN %s AND %s
        AND pi.company = %s AND pi.docstatus = 1
        AND (ptc.account_head LIKE '%%Withholding%%' OR ptc.description LIKE '%%WHT%%')
        GROUP BY pi.posting_date
    """

    # Build consolidated VAT query
    vat_query = """
        SELECT
            si.posting_date,
            ABS(SUM(stc.tax_amount)) as amount
        FROM `tabSales Invoice` si
        JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
        WHERE si.posting_date BETWEEN %s AND %s
        AND si.company = %s AND si.docstatus = 1
        AND (stc.account_head LIKE '%%VAT%%' OR stc.description LIKE '%%VAT%%')
        GROUP BY si.posting_date
    """

    # Execute WHT query for all months at once
    wht_results = {}
    for params in months_query_params:
        wht_data = frappe.db.sql(wht_query, params, as_dict=True)
        if wht_data and wht_data[0].amount:
            month_dt = datetime.strptime(params[0], '%Y-%m-%d')
            month_label = month_dt.strftime('%b')
            wht_results[month_label] = flt(wht_data[0].amount)

    # Execute VAT query for all months at once
    vat_results = {}
    for params in months_query_params:
        vat_data = frappe.db.sql(vat_query, params, as_dict=True)
        if vat_data and vat_data[0].amount:
            month_dt = datetime.strptime(params[0], '%Y-%m-%d')
            month_label = month_dt.strftime('%b')
            vat_results[month_label] = flt(vat_data[0].amount)

    # TOT query - handle gracefully
    tot_results = {}
    try:
        settings = frappe.get_cached_doc("Compliance Setting")
        if settings.get("tot_account"):
            tot_query = """
                SELECT
                    si.posting_date,
                    ABS(SUM(stc.tax_amount)) as amount
                FROM `tabSales Invoice` si
                JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
                WHERE si.posting_date BETWEEN %s AND %s
                AND si.company = %s AND si.docstatus = 1 AND stc.account_head = %s
                GROUP BY si.posting_date
            """
            for params in months_query_params:
                tot_data = frappe.db.sql(tot_query, params + (settings.tot_account,), as_dict=True)
                if tot_data and tot_data[0].amount:
                    month_dt = datetime.strptime(params[0], '%Y-%m-%d')
                    month_label = month_dt.strftime('%b')
                    tot_results[month_label] = flt(tot_data[0].amount)
        else:
            pass  # TOT not configured, leave empty
    except frappe.DoesNotExistError:
        pass  # Settings doc doesn't exist
    except AttributeError:
        pass  # Settings doc missing expected attributes

    # Build tax arrays in chronological order
    taxes = {
        "wht": [{"month": label, "amount": wht_results.get(label, 0)} for label in months_ordered],
        "vat": [{"month": label, "amount": vat_results.get(label, 0)} for label in months_ordered],
        "tot": [{"month": label, "amount": tot_results.get(label, 0)} for label in months_ordered]
    }

    result = {
        "revenue": revenue,
        "expenses": expenses,
        "cash_flow": cash_flow,
        "taxes": taxes
    }

    frappe.cache().set_value(cache_key, result, expires_in_sec=3600)
    return result