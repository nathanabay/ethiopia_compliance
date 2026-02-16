import frappe
from frappe.utils import today, add_days, get_first_day, get_last_day, flt
from ethiopia_compliance.utils import get_ec_date


@frappe.whitelist()
def get_dashboard_data():
    """
    Get all data for compliance dashboard
    """
    company = frappe.defaults.get_user_default("Company")
    if not company:
        return {}
    
    # Get current month dates
    today_date = today()
    month_start = get_first_day(today_date)
    month_end = get_last_day(today_date)
    
    # Get Ethiopian date
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
    """
    Get tax summary for the period
    """
    # WHT Summary
    wht_data = frappe.db.sql("""
        SELECT 
            SUM(base_total) as total_purchases,
            SUM(base_tax_total) as total_wht
        FROM `tabPurchase Invoice`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date), as_dict=True)
    
    # VAT Summary
    vat_data = frappe.db.sql("""
        SELECT 
            SUM(base_net_total) as total_sales,
            SUM(base_total_taxes_and_charges) as total_vat
        FROM `tabSales Invoice`
        WHERE company = %s
        AND posting_date BETWEEN %s AND %s
        AND docstatus = 1
    """, (company, from_date, to_date), as_dict=True)
    
    return {
        'wht': {
            'total_purchases': flt(wht_data[0].total_purchases) if wht_data else 0,
            'total_wht': flt(wht_data[0].total_wht) if wht_data else 0
        },
        'vat': {
            'total_sales': flt(vat_data[0].total_sales) if vat_data else 0,
            'total_vat': flt(vat_data[0].total_vat) if vat_data else 0
        }
    }


def get_recent_documents(company, limit=10):
    """
    Get recent tax-relevant documents
    """
    documents = []
    
    # Recent Sales Invoices
    sales_invoices = frappe.get_all('Sales Invoice',
        filters={'company': company, 'docstatus': 1},
        fields=['name', 'posting_date', 'customer', 'grand_total'],
        order_by='posting_date desc',
        limit=limit
    )
    
    for inv in sales_invoices:
        documents.append({
            'type': 'Sales Invoice',
            'name': inv.name,
            'date': inv.posting_date,
            'party': inv.customer,
            'amount': inv.grand_total
        })
    
    # Recent Purchase Invoices
    purchase_invoices = frappe.get_all('Purchase Invoice',
        filters={'company': company, 'docstatus': 1},
        fields=['name', 'posting_date', 'supplier', 'grand_total'],
        order_by='posting_date desc',
        limit=limit
    )
    
    for inv in purchase_invoices:
        documents.append({
            'type': 'Purchase Invoice',
            'name': inv.name,
            'date': inv.posting_date,
            'party': inv.supplier,
            'amount': inv.grand_total
        })
    
    # Sort by date
    documents.sort(key=lambda x: x['date'], reverse=True)
    
    return documents[:limit]


def get_compliance_status(company):
    """
    Check compliance status
    """
    status = {
        'settings_configured': False,
        'calendar_enabled': False,
        'fiscal_year_set': False
    }
    
    # Check if compliance settings are configured
    try:
        settings = frappe.get_single('Compliance Setting')
        if settings.wht_rate and settings.vat_rate:
            status['settings_configured'] = True
        if settings.enable_ethiopian_calendar:
            status['calendar_enabled'] = True
    except:
        pass
    
    # Check if fiscal year is set
    if frappe.db.exists('Fiscal Year', '2017 E.C.'):
        status['fiscal_year_set'] = True
    
    return status
