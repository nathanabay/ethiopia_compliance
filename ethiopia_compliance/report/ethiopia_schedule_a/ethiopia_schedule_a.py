# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Ethiopia Schedule A — Employment Income Tax Report

Proclamation No. 979/2016 (as amended by Proclamation No. 1395/2017):
Employment income tax brackets for the tax year:

    0 – 2,000 ETB:        0%
    2,001 – 4,000 ETB:   15%
    4,001 – 7,000 ETB:   20%
    7,001 – 10,000 ETB:  25%
    10,001 – 14,000 ETB: 30%
    Above 14,000 ETB:     35%

This report shows per-employee annual earnings and the legally computed
PAYE liability per the above slabs. Any difference between the pre-collected
tax (from Salary Slips) and the Schedule A computation is flagged for review.
"""

import frappe
from frappe import _
from frappe.utils import flt
from collections import defaultdict


BASIC_COMPONENTS = {"Basic Salary", "Basic"}
TRANSPORT_COMPONENTS = {"Transport Allowance", "Transport", "Transportation Allowance"}
OVERTIME_COMPONENTS = {"Overtime", "Overtime Pay"}
INCOME_TAX_COMPONENTS = {"Income Tax", "PAYE", "Employment Income Tax"}
COST_SHARING_COMPONENTS = {"Cost Sharing", "Cost Sharing (Employee)"}
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}

# ─── Legal Employment Income Tax Slabs (Proclamation No. 979/2016 Schedule A) ─
# Each tuple: (ceiling, rate_up_to_ceiling)
# Special handling for the final tier (no ceiling)
TAX_SLABS = [
    (2000,  0.00),
    (4000,  0.15),
    (7000,  0.20),
    (10000, 0.25),
    (14000, 0.30),
]


def execute(filters=None):
    if filters is None:
        filters = {}

    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"fieldname": "emp_tin",       "label": _("Employee TIN"),           "fieldtype": "Data",     "width": 140},
        {"fieldname": "emp_name",     "label": _("Employee Name"),         "fieldtype": "Data",     "width": 200},
        {"fieldname": "fiscal_year",  "label": _("Fiscal Year"),           "fieldtype": "Data",     "width": 100},
        {"fieldname": "basic_salary",  "label": _("Basic Salary"),          "fieldtype": "Currency", "width": 120},
        {"fieldname": "transport_taxable", "label": _("Taxable Transport"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "overtime",      "label": _("Overtime"),              "fieldtype": "Currency", "width": 100},
        {"fieldname": "other_taxable", "label": _("Other Taxable"),         "fieldtype": "Currency", "width": 120},
        {"fieldname": "total_gross",   "label": _("Total Gross Pay"),       "fieldtype": "Currency", "width": 130},
        {"fieldname": "emp_pension",   "label": _("Employee Pension (7%)"),"fieldtype": "Currency", "width": 150},
        {"fieldname": "taxable_income","label": _("Taxable Income"),        "fieldtype": "Currency", "width": 130},
        {"fieldname": "computed_tax",  "label": _("Schedule A Tax (ETB)"),  "fieldtype": "Currency", "width": 160},
        {"fieldname": "tax_withheld",  "label": _("PAYE Withheld (ETB)"),   "fieldtype": "Currency", "width": 160},
        {"fieldname": "tax_difference","label": _("Difference (ETB)"),     "fieldtype": "Currency", "width": 130},
        {"fieldname": "net_pay",       "label": _("Net Pay"),               "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    if not filters.get("company"):
        frappe.throw(_("Company filter is required."))
    if not filters.get("from_date"):
        frappe.throw(_("From Date filter is required."))
    if not filters.get("to_date"):
        frappe.throw(_("To Date filter is required."))
    if not filters.get("fiscal_year"):
        frappe.throw(_("Fiscal Year filter is required."))

    conditions = ["docstatus = 1"]
    values = {
        "company": filters["company"],
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }

    conditions.append("company = %(company)s")
    conditions.append("start_date >= %(from_date)s")
    conditions.append("end_date <= %(to_date)s")

    slips = frappe.db.sql("""
        SELECT
            name,
            employee_name as emp_name,
            employee as emp_id,
            gross_pay,
            net_pay
        FROM `tabSalary Slip`
        WHERE {where}
    """.format(where=" AND ".join(conditions)), values, as_dict=True)

    if not slips:
        return [], []

    # Batch fetch employee TINs (1 query instead of N)
    emp_ids = list({s.emp_id for s in slips})
    emp_tins = {}
    for name, tax_id in frappe.db.get_values("Employee", emp_ids, ["name", "tax_id"]):
        emp_tins[name] = tax_id or ""

    # Batch fetch salary components (1 query)
    slip_names = [s.name for s in slips]
    all_components = frappe.db.sql("""
        SELECT parent, salary_component, amount, type
        FROM `tabSalary Detail`
        WHERE parent IN %(slip_names)s
    """, {"slip_names": slip_names}, as_dict=True)

    components_by_parent = defaultdict(list)
    for c in all_components:
        components_by_parent[c.parent].append(c)

    data = []
    for slip in slips:
        components = components_by_parent.get(slip.name, [])
        emp_tin = emp_tins.get(slip.emp_id, "")

        basic = transport = overtime = other = tax_withheld = cost_share = emp_pension = 0.0

        for c in components:
            if c.salary_component in BASIC_COMPONENTS:
                basic += flt(c.amount)
            elif c.salary_component in TRANSPORT_COMPONENTS:
                transport += flt(c.amount)
            elif c.salary_component in OVERTIME_COMPONENTS:
                overtime += flt(c.amount)
            elif c.salary_component in INCOME_TAX_COMPONENTS:
                tax_withheld += flt(c.amount)
            elif c.salary_component in COST_SHARING_COMPONENTS:
                cost_share += flt(c.amount)
            elif c.salary_component in EMP_PENSION_COMPONENTS:
                emp_pension += flt(c.amount)
            elif c.type == "Earning" and flt(c.amount) > 0:
                other += flt(c.amount)

        total_gross = basic + transport + overtime + other
        taxable_income = total_gross - emp_pension
        computed_tax = calculate_schedule_a_tax(taxable_income)
        tax_difference = tax_withheld - computed_tax

        data.append({
            "emp_tin":         emp_tin,
            "emp_name":        slip.emp_name,
            "fiscal_year":     filters.get("fiscal_year"),
            "basic_salary":    basic,
            "transport_taxable": transport,
            "overtime":        overtime,
            "other_taxable":   other,
            "total_gross":     total_gross,
            "emp_pension":     emp_pension,
            "taxable_income":  taxable_income,
            "computed_tax":    computed_tax,
            "tax_withheld":    tax_withheld,
            "tax_difference":  tax_difference,
            "net_pay":         flt(slip.net_pay),
        })

    return data


def calculate_schedule_a_tax(monthly_taxable_income):
    """Compute employment income tax using the Schedule A slabs.

    Proclamation No. 979/2016 Schedule A (as amended):

        0 – 2,000 ETB:        0%
        2,001 – 4,000 ETB:   15%  (on the band above 2,000)
        4,001 – 7,000 ETB:   20%  (on the band above 4,000)
        7,001 – 10,000 ETB:  25%  (on the band above 7,000)
        10,001 – 14,000 ETB: 30%  (on the band above 10,000)
        Above 14,000 ETB:     35%  (on the band above 14,000)

    Args:
        monthly_taxable_income (float): Monthly taxable income in ETB.

    Returns:
        float: Annual tax liability (monthly income * 12 * slab rate approach
               applied to annual total), rounded to 2 decimal places.
    """
    if monthly_taxable_income <= 0:
        return 0.0

    # Annualise for proper slab application (tax is annual)
    annual_taxable = monthly_taxable_income * 12
    annual_tax = _compute_annual_slab_tax(annual_taxable)

    # Return monthly equivalent (rounded)
    return round(annual_tax / 12, 2)


def _compute_annual_slab_tax(annual_taxable_income):
    """Apply Schedule A slabs cumulatively to annual income.

    Args:
        annual_taxable_income (float): Annual taxable income in ETB.

    Returns:
        float: Total annual tax in ETB.
    """
    if annual_taxable_income <= 2000:
        return 0.0

    tax = 0.0
    remaining = annual_taxable_income
    previous_ceiling = 0.0

    for ceiling, rate in TAX_SLABS:
        if remaining <= 0:
            break
        band_income = min(remaining, ceiling - previous_ceiling)
        if annual_taxable_income > previous_ceiling:
            taxable_in_band = min(band_income, annual_taxable_income - previous_ceiling)
            if taxable_in_band > 0:
                tax += taxable_in_band * rate
        remaining -= band_income
        previous_ceiling = ceiling

        if annual_taxable_income <= ceiling:
            break

    # Final tier (above 14,000) — 35%
    if annual_taxable_income > 14000:
        tax += (annual_taxable_income - 14000) * 0.35

    return tax