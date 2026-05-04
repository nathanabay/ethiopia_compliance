# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt

# ─── Payroll aggregation components ───────────────────────────────────────────
INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}

# ─── Corporate income tax components ───────────────────────────────────────
REVENUE_COMPONENTS = {"Sales", "Service Revenue", "Other Income"}
COST_COMPONENTS = {"Cost of Goods Sold", "Cost of Services", "Direct Costs"}


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "employee",
            "label": _("Employee"),
            "fieldtype": "Link",
            "options": "Employee",
            "width": 120
        },
        {
            "fieldname": "employee_name",
            "label": _("Employee Name"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "tin_number",
            "label": _("TIN Number"),
            "fieldtype": "Data",
            "width": 120
        },
        {
            "fieldname": "total_gross_pay",
            "label": _("Total Gross Pay"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_taxable_income",
            "label": _("Total Taxable Income"),
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "fieldname": "total_income_tax",
            "label": _("Total Income Tax"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "total_pension",
            "label": _("Total Pension (7%)"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "net_pay",
            "label": _("Total Net Pay"),
            "fieldtype": "Currency",
            "width": 120
        },
        # ─── Corporate / MAT columns ─────────────────────────────────────────
        {
            "fieldname": "gross_sales",
            "label": _("Gross Sales"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "total_revenue",
            "label": _("Total Revenue"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "total_expenses",
            "label": _("Total Expenses"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "net_profit",
            "label": _("Net Profit"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "schedule_c_tax",
            "label": _("Schedule C Tax (30%)"),
            "fieldtype": "Currency",
            "width": 150
        },
        {
            "fieldname": "mat_liability",
            "label": _("MAT Liability (2.5% Gross Sales)"),
            "fieldtype": "Currency",
            "width": 200
        },
        {
            "fieldname": "tax_after_mat",
            "label": _("Tax After MAT"),
            "fieldtype": "Currency",
            "width": 130
        },
        {
            "fieldname": "mat_applied",
            "label": _("MAT Applied"),
            "fieldtype": "Check",
            "width": 100
        }
    ]


def get_data(filters):
    if not filters.get("year") or not filters.get("company"):
        frappe.throw(_("Company and Year are required filters."))

    year = int(filters.get("year"))
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # ─── A. Payroll aggregation ───────────────────────────────────────────────
    slips_agg = frappe.db.sql("""
        SELECT
            ss.employee,
            ss.employee_name,
            emp.tax_id as tin_number,
            SUM(ss.gross_pay) as total_gross,
            SUM(ss.net_pay) as total_net
        FROM `tabSalary Slip` ss
        LEFT JOIN `tabEmployee` emp ON ss.employee = emp.name
        WHERE ss.company = %(company)s
          AND ss.start_date BETWEEN %(start_date)s AND %(end_date)s
          AND ss.docstatus = 1
        GROUP BY ss.employee
    """, {
        "company": filters.get("company"),
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)

    final_data = {}
    for row in slips_agg:
        final_data[row.employee] = {
            "employee": row.employee,
            "employee_name": row.employee_name,
            "tin_number": row.tin_number,
            "total_gross_pay": flt(row.total_gross),
            "total_taxable_income": 0,
            "total_income_tax": 0,
            "total_pension": 0,
            "net_pay": flt(row.total_net),
            # Corporate / MAT fields — filled from GL for the company
            "gross_sales": 0.0,
            "total_revenue": 0.0,
            "total_expenses": 0.0,
            "net_profit": 0.0,
            "schedule_c_tax": 0.0,
            "mat_liability": 0.0,
            "tax_after_mat": 0.0,
            "mat_applied": 0
        }

    # ─── B. Payroll components aggregate ───────────────────────────────────────
    components_agg = frappe.db.sql("""
        SELECT
            ss.employee,
            sd.salary_component,
            SUM(sd.amount) as total_amount
        FROM `tabSalary Slip` ss
        JOIN `tabSalary Detail` sd ON sd.parent = ss.name
        WHERE ss.company = %(company)s
          AND ss.start_date BETWEEN %(start_date)s AND %(end_date)s
          AND ss.docstatus = 1
        GROUP BY ss.employee, sd.salary_component
    """, {
        "company": filters.get("company"),
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)

    for row in components_agg:
        if row.employee in final_data:
            if row.salary_component in INCOME_TAX_COMPONENTS:
                final_data[row.employee]["total_income_tax"] += flt(row.total_amount)
            if row.salary_component in PENSION_COMPONENTS:
                final_data[row.employee]["total_pension"] += flt(row.total_amount)

    for emp_data in final_data.values():
        emp_data["total_taxable_income"] = \
            emp_data["total_gross_pay"] - emp_data["total_pension"]

    # ─── C. Corporate income tax & MAT (one-shot aggregation) ─────────────────
    corporate_data = _get_corporate_mat_data(
        company=filters.get("company"),
        start_date=start_date,
        end_date=end_date
    )

    # Merge corporate/MAT data into every employee row (report shows both)
    for emp_data in final_data.values():
        emp_data.update(corporate_data)

    return list(final_data.values())


def _get_corporate_mat_data(company, start_date, end_date):
    """Compute gross sales, net profit, Schedule C tax, and MAT.

    Uses frappe.qb for a single-pass aggregate query against GL Entry.
    Proclamation No. 979/2016 Art. 23: MAT applies when net profit tax
    is less than 2.5% of gross sales.

    Returns a dict with keys:
        gross_sales, total_revenue, total_expenses, net_profit,
        schedule_c_tax, mat_liability, tax_after_mat, mat_applied
    """
    # Fetch MAT rate from Compliance Setting
    try:
        settings = frappe.get_cached_doc("Compliance Setting")
        mat_rate = (flt(settings.mat_rate) or 2.5) / 100
    except Exception:
        mat_rate = 0.025  # fallback 2.5%

    SCHEDULE_C_RATE = 0.30  # Art. 22 / Schedule C — 30% flat rate

    # Single aggregate query: sum credit and debit by account nature
    # Revenue accounts have credit balances, expense accounts have debit balances
    agg = frappe.db.sql("""
        SELECT
            SUM(CASE
                WHEN acc.account_type IN ('Revenue', 'Income Account')
                     OR acc.parent_account LIKE '%Revenue%'
                     OR acc.parent_account LIKE '%Income%'
                THEN gl.debit - gl.credit
                ELSE 0
            END) AS total_revenue,

            SUM(CASE
                WHEN acc.account_type IN ('Cost of Goods Sold', 'Direct Expenses',
                                           'Expense Account', 'Expenses')
                     OR acc.parent_account LIKE '%Cost%'
                     OR acc.parent_account LIKE '%Expense%'
                THEN gl.debit
                ELSE 0
            END) AS total_expenses,

            SUM(CASE
                WHEN acc.account_type IN ('Revenue', 'Income Account')
                     OR acc.parent_account LIKE '%Revenue%'
                     OR acc.parent_account LIKE '%Income%'
                THEN gl.credit - gl.debit
                ELSE 0
            END) AS gross_sales
        FROM `tabGL Entry` gl
        JOIN `tabAccount` acc ON gl.account = acc.name
        WHERE gl.company = %(company)s
          AND gl.posting_date BETWEEN %(start_date)s AND %(end_date)s
          AND gl.docstatus = 1
    """, {
        "company": company,
        "start_date": start_date,
        "end_date": end_date
    }, as_dict=True)

    if not agg:
        return _empty_corporate_result()

    row = agg[0]
    gross_sales = flt(row.gross_sales) or 0.0
    total_revenue = flt(row.total_revenue) or 0.0
    total_expenses = flt(row.total_expenses) or 0.0

    net_profit = gross_sales - total_expenses
    if net_profit <= 0:
        return _empty_corporate_result(mat_rate=mat_rate)

    schedule_c_tax = net_profit * SCHEDULE_C_RATE
    mat_liability = gross_sales * mat_rate

    mat_applied = mat_liability > schedule_c_tax
    tax_after_mat = mat_liability if mat_applied else schedule_c_tax

    return {
        "gross_sales": gross_sales,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "schedule_c_tax": schedule_c_tax,
        "mat_liability": mat_liability,
        "tax_after_mat": tax_after_mat,
        "mat_applied": 1 if mat_applied else 0
    }


def _empty_corporate_result(mat_rate=0.025):
    return {
        "gross_sales": 0.0,
        "total_revenue": 0.0,
        "total_expenses": 0.0,
        "net_profit": 0.0,
        "schedule_c_tax": 0.0,
        "mat_liability": 0.0,
        "tax_after_mat": 0.0,
        "mat_applied": 0
    }