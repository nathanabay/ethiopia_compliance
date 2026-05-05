# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

"""
Tax Percentage of Completion (PoC) — Long-Term Contract Revenue Recognition

For long-term contracts (construction, engineering, project-based services),
Ethiopian tax law requires revenue to be recognized based on the percentage
of completion method.

Formula:
    PoC % = (Actual Costs to Date / Total Estimated Costs) × 100
    Taxable Revenue = Contract Value × PoC % − Revenue Recognized to Date

This DocType links to ERPNext Projects and computes the PoC for each
reporting period (monthly/quarterly/annually).
"""

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, today, now_datetime, date_diff, get_first_day, get_last_day


class TaxPercentageofCompletion(Document):
    """Track Percentage of Completion for long-term tax contract recognition.

    Linked to a Project via project_id. Each record represents one
    measurement period (e.g. a month or quarter).
    """

    def validate(self):
        self._validate_dates()
        self._compute_poc()

    def _validate_dates(self):
        if self.period_from and self.period_to:
            if getdate(self.period_from) > getdate(self.period_to):
                frappe.throw(_("Period From cannot be after Period To."))

        if self.estimated_total_cost and self.estimated_total_cost <= 0:
            frappe.throw(_("Estimated Total Cost must be greater than zero."))

        if self.contract_value and self.contract_value < 0:
            frappe.throw(_("Contract Value cannot be negative."))

    def _compute_poc(self):
        """Compute PoC percentage and recognized revenue.

        Formula: PoC % = cumulative_costs_to_date / estimated_total_cost * 100
        """
        if not self.estimated_total_cost or self.estimated_total_cost <= 0:
            self.poc_percentage = 0.0
            self.taxable_revenue_period = 0.0
            return

        self.poc_percentage = flt(
            self.cumulative_costs_to_date / self.estimated_total_cost * 100,
            6
        )

        # Cap at 100%
        if self.poc_percentage > 100:
            self.poc_percentage = 100.0

        # Total taxable revenue recognized to date
        self.cumulative_revenue_recognized = flt(
            self.contract_value * self.poc_percentage / 100,
            2
        )

        # Revenue for this period = current cumulative − prior cumulative
        self.taxable_revenue_period = flt(
            self.cumulative_revenue_recognized - (self.prior_revenue_recognized or 0),
            2
        )

        if self.taxable_revenue_period < 0:
            self.taxable_revenue_period = 0.0

    def get_cost_to_date_from_gl(self):
        """Pull actual costs from GL Entry for the linked project.

        Returns:
            float: total debits to project cost accounts
        """
        if not self.project:
            return 0.0

        costs = frappe.db.sql("""
            SELECT SUM(gl.debit) as total_cost
            FROM `tabGL Entry` gl
            JOIN `tabAccount` acc ON gl.account = acc.name
            WHERE gl.project = %(project)s
              AND gl.posting_date BETWEEN %(period_from)s AND %(period_to)s
              AND gl.docstatus = 1
              AND (
                  acc.account_type IN ('Expense Account', 'Fixed Asset', 'Cost of Goods Sold')
                  OR acc.parent_account LIKE '%%Direct Cost%%'
                  OR acc.parent_account LIKE '%%Project Cost%%'
              )
        """, {
            "project": self.project,
            "period_from": self.period_from,
            "period_to": self.period_to
        }, as_dict=True)

        return flt(costs[0].total_cost) if costs and costs[0].total_cost else 0.0


@frappe.whitelist(force_types=True)
def calculate_poc(project: str, period_from: str, period_to: str,
                   contract_value: float, prior_revenue: float = 0) -> dict:
    """API: compute PoC for a contract without saving.

    Args:
        project (str): Project name
        period_from (str): period start date
        period_to (str): period end date
        contract_value (float): total contract value
        prior_revenue (float): revenue already recognized in prior periods

    Returns:
        dict: {poc_percentage, cumulative_revenue, taxable_revenue_period}
    """
    frappe.only_for("Account Manager", "System Manager")
    try:
        doc = frappe.new_doc("Tax Percentage of Completion")
        doc.project = project
        doc.period_from = period_from
        doc.period_to = period_to
        doc.contract_value = flt(contract_value)
        doc.prior_revenue_recognized = flt(prior_revenue)

        # Auto-fetch costs from GL
        doc.cumulative_costs_to_date = doc.get_cost_to_date_from_gl()
        doc._compute_poc()

        return {
            "poc_percentage": doc.poc_percentage,
            "cumulative_costs_to_date": doc.cumulative_costs_to_date,
            "cumulative_revenue_recognized": doc.cumulative_revenue_recognized,
            "taxable_revenue_period": doc.taxable_revenue_period,
        }

    except Exception:
        frappe.log_error(frappe.get_traceback(),
            "Ethiopia Compliance Error: calculate_poc"
        )
        frappe.throw(_("Failed to compute Percentage of Completion."))