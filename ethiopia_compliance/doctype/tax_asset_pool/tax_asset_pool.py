# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Tax Asset Pool — Ethiopian Tax Depreciation

Under Ethiopian tax law (Proclamation No. 979/2016 and Income Tax Rules):
- Initial/initial allowance: One-time deduction on acquisition (typically 50% for machinery)
- Annual depreciation schedule: differs from accounting straight-line

Asset categories and their tax depreciation rates:
  - Buildings: 5% straight-line (20 years)
  - Machinery & Equipment: 25% declining balance
  - Motor Vehicles: 25% declining balance
  - Office Equipment: 25% declining balance
  - Computer Hardware: 50% declining balance
  - Intangible Assets: 10% straight-line (or contractual life)
  - Leased Assets: per lease agreement terms

This DocType creates a tax-specific asset register and computes the
depreciation schedule per Ethiopian tax rules, distinct from the
accounting (ERPNext Asset) depreciation.
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, date_diff, add_years, add_months, now_datetime


class TaxAssetPool(Document):
    """Tax-specific asset depreciation register per Ethiopian tax law.

    Each record represents a pool of similar assets (by category) for which
    a single annual tax depreciation schedule is computed.
    """

    def before_save(self):
        self._compute_depreciation_schedule()

    def validate(self):
        self._validate_asset()
        if not self.asset_category:
            frappe.throw(_("Asset Category is required."))

    def _validate_asset(self):
        if self.total_cost and self.total_cost < 0:
            frappe.throw(_("Total Cost must be a positive number."))
        if self.useful_life_years and self.useful_life_years < 0:
            frappe.throw(_("Useful Life (Years) must be positive."))

    def _compute_depreciation_schedule(self):
        """Recompute the depreciation table from current values.

        Called on before_save so the table is always current.
        """
        self.tax_depreciation_schedule = []

        if not self.total_cost or self.total_cost <= 0:
            return

        # Initial allowance (first-year bonus deduction)
        initial_allowance = self._compute_initial_allowance()
        if initial_allowance > 0:
            self.append("tax_depreciation_schedule", {
                "depreciation_year": "Initial Allowance",
                "fiscal_year": "",
                "opening_wdv": self.total_cost,
                "depreciation_rate": self.initial_allowance_rate,
                "depreciation_amount": initial_allowance,
                "accumulated_depreciation": initial_allowance,
                "closing_wdv": self.total_cost - initial_allowance,
                "depreciation_method": "Initial Allowance"
            })
            opening_wdv = self.total_cost - initial_allowance
        else:
            opening_wdv = self.total_cost

        # Annual depreciation
        annual_rate = self._get_annual_tax_rate()
        remaining_wdv = opening_wdv
        year = 1

        while remaining_wdv > 0.01 and year <= 30:
            dep_amount = remaining_wdv * annual_rate
            if dep_amount < 0.01:
                break

            accumulated = sum(
                flt(r.depreciation_amount)
                for r in self.tax_depreciation_schedule
            )

            self.append("tax_depreciation_schedule", {
                "depreciation_year": f"Year {year}",
                "fiscal_year": "",
                "opening_wdv": remaining_wdv,
                "depreciation_rate": annual_rate * 100,
                "depreciation_amount": dep_amount,
                "accumulated_depreciation": accumulated + dep_amount,
                "closing_wdv": remaining_wdv - dep_amount,
                "depreciation_method": self.depreciation_method
            })

            remaining_wdv = remaining_wdv - dep_amount
            year += 1

    def _compute_initial_allowance(self):
        """One-time initial allowance on acquisition.

        Under Ethiopian tax rules: 50% for machinery/equipment,
        25% for commercial buildings, 0 for others.
        """
        if not self.total_cost:
            return 0.0
        rate = flt(self.initial_allowance_rate) or 0.0
        return flt(self.total_cost * rate / 100)

    def _get_annual_tax_rate(self):
        """Return annual tax depreciation rate based on asset category.

        Ethiopian Income Tax Rules — standard rates:
            Buildings:           5% straight-line
            Machinery/Equipment: 25% declining balance
            Motor Vehicles:      25% declining balance
            Office Equipment:   25% declining balance
            Computer Hardware:   50% declining balance
            Intangible Assets:   10% straight-line (or contractual)
        """
        rates = {
            "Buildings":          0.05,
            "Machinery":          0.25,
            "Equipment":          0.25,
            "Motor Vehicles":     0.25,
            "Office Equipment":   0.25,
            "Computer Hardware":  0.50,
            "Intangible Assets":  0.10,
        }
        return rates.get(self.asset_category, 0.25)  # default 25%

    def get_tax_depreciation_for_year(self, fiscal_year):
        """Return the depreciation amount for a given fiscal year.

        Args:
            fiscal_year (str): e.g. "2026"

        Returns:
            float: depreciation amount for that year
        """
        for row in self.tax_depreciation_schedule:
            if row.fiscal_year == fiscal_year:
                return flt(row.depreciation_amount)
        return 0.0

    def get_accumulated_depreciation(self, as_of_date=None):
        """Return total accumulated depreciation up to as_of_date.

        Args:
            as_of_date (str): date string YYYY-MM-DD

        Returns:
            float: accumulated depreciation
        """
        if not as_of_date:
            as_of_date = today()

        total = 0.0
        for row in self.tax_depreciation_schedule:
            if row.get("fiscal_year") and row.fiscal_year <= fiscal_year_to_str(as_of_date):
                total += flt(row.depreciation_amount)

        # Fallback: sum all rows if no fiscal_year set
        if total == 0.0:
            total = sum(flt(r.depreciation_amount) for r in self.tax_depreciation_schedule)
        return total


def fiscal_year_to_str(date_str):
    """Extract year string from date string."""
    d = getdate(date_str)
    return str(d.year)


@frappe.whitelist()
def calculate_pool_depreciation(asset_category, total_cost,
                                 initial_allowance_rate=0):
    """API: compute depreciation schedule for a proposed asset pool.

    Args:
        asset_category (str): category name
        total_cost (float): total pool cost
        initial_allowance_rate (float): initial allowance percentage

    Returns:
        dict: {schedule: [...], total_depreciation: float, tax_wdv: float}
    """
    try:
        doc = frappe.new_doc("Tax Asset Pool")
        doc.asset_category = asset_category
        doc.total_cost = flt(total_cost)
        doc.initial_allowance_rate = flt(initial_allowance_rate)
        doc._compute_depreciation_schedule()

        rows = []
        total_dep = 0.0
        for r in doc.tax_depreciation_schedule:
            rows.append({
                "year": r.depreciation_year,
                "opening_wdv": r.opening_wdv,
                "rate": r.depreciation_rate,
                "amount": r.depreciation_amount,
                "accumulated": r.accumulated_depreciation,
                "closing_wdv": r.closing_wdv,
                "method": r.depreciation_method
            })
            total_dep += flt(r.depreciation_amount)

        tax_wdv = flt(total_cost) - total_dep
        return {"schedule": rows, "total_depreciation": total_dep, "tax_wdv": tax_wdv}

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Ethiopia Compliance Error: calculate_pool_depreciation"
        )
        frappe.throw(_("Failed to compute tax depreciation schedule."))