# Copyright (c) 2026, Bespo and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days, today, date_diff


def execute(filters=None):
	if filters is None:
		filters = {}

	columns = [
		{"fieldname": "month", "label": _("Month"), "fieldtype": "Data", "width": 130},
		{"fieldname": "month_end", "label": _("Month End"), "fieldtype": "Date", "width": 100},
		{"fieldname": "emp_pension_total", "label": _("Emp. Pension (7%)"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "org_pension_total", "label": _("Org. Pension (11%)"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "total_pension", "label": _("Total Pension Due"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "amount_remitted", "label": _("Amount Remitted"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "outstanding", "label": _("Outstanding"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "last_remittance_date", "label": _("Last Remittance"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days_elapsed", "label": _("Days Elapsed"), "fieldtype": "Int", "width": 100},
		{"fieldname": "risk_level", "label": _("Risk Level"), "fieldtype": "Data", "width": 130}
	]

	if not filters.get("company"):
		frappe.throw(_("Company filter is required."))
	if not filters.get("from_date"):
		frappe.throw(_("From Date filter is required."))
	if not filters.get("to_date"):
		frappe.throw(_("To Date filter is required."))

	# Get monthly pension totals from submitted salary slips
	slips = frappe.db.sql("""
		SELECT
			DATE_FORMAT(ss.start_date, '%%Y-%%m') as month_key,
			LAST_DAY(ss.start_date) as month_end,
			ss.name as slip_name
		FROM `tabSalary Slip` ss
		WHERE ss.docstatus = 1
			AND ss.company = %(company)s
			AND ss.start_date >= %(from_date)s
			AND ss.end_date <= %(to_date)s
		ORDER BY month_key
	""", {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"to_date": filters["to_date"]
	}, as_dict=True)

	if not slips:
		return columns, []

	slip_names = [s.slip_name for s in slips]

	# Get pension components
	EMP_PENSION = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}
	ORG_PENSION = {"Pension (Employer)", "Employer Pension", "Employer Pension (11%)"}

	components = frappe.db.sql("""
		SELECT sd.parent, sd.salary_component, sd.amount
		FROM `tabSalary Detail` sd
		WHERE sd.parent IN %(slip_names)s
	""", {"slip_names": slip_names}, as_dict=True)

	# Aggregate by month
	monthly = {}
	for s in slips:
		mk = s.month_key
		if mk not in monthly:
			monthly[mk] = {
				"month": mk,
				"month_end": s.month_end,
				"emp_pension": 0.0,
				"org_pension": 0.0,
				"slip_names": []
			}
		monthly[mk]["slip_names"].append(s.slip_name)

	slip_to_month = {s.slip_name: s.month_key for s in slips}

	for c in components:
		mk = slip_to_month.get(c.parent)
		if mk:
			if c.salary_component in EMP_PENSION:
				monthly[mk]["emp_pension"] += flt(c.amount)
			elif c.salary_component in ORG_PENSION:
				monthly[mk]["org_pension"] += flt(c.amount)

	# Get pension remittance payments
	remittances = frappe.db.sql("""
		SELECT
			pe.name,
			pe.posting_date,
			pe.paid_amount,
			YEAR(pe.posting_date) as remit_year,
			MONTH(pe.posting_date) as remit_month
		FROM `tabPayment Entry` pe
		WHERE pe.docstatus = 1
			AND pe.company = %(company)s
			AND pe.payment_type = 'Pay'
			AND (
				pe.paid_to LIKE %(poessa)s
				OR pe.party LIKE %(poessa)s
				OR pe.paid_to_account_head LIKE %(poessa)s
			)
			AND pe.posting_date >= %(from_date)s
		ORDER BY pe.posting_date
	""", {
		"company": filters["company"],
		"from_date": filters["from_date"],
		"poessa": "%%POESSA%%"
	}, as_dict=True)

	# Aggregate remittances by month
	remit_by_month = {}
	for r in remittances:
		mk = f"{r.remit_year}-{r.remit_month:02d}"
		if mk not in remit_by_month:
			remit_by_month[mk] = {"amount": 0.0, "last_date": r.posting_date}
		remit_by_month[mk]["amount"] += flt(r.paid_amount)
		if r.posting_date > remit_by_month[mk]["last_date"]:
			remit_by_month[mk]["last_date"] = r.posting_date

	# Build final data with risk levels
	data = []
	_today = getdate(today())

	for mk in sorted(monthly.keys()):
		m = monthly[mk]
		emp_pension = m["emp_pension"]
		org_pension = m["org_pension"]
		total_pension = emp_pension + org_pension
		remitted = remit_by_month.get(mk, {}).get("amount", 0.0)
		last_remit = remit_by_month.get(mk, {}).get("last_date")
		outstanding = total_pension - remitted

		# Days elapsed since month end (or last remittance)
		month_end = getdate(m["month_end"])
		if last_remit:
			days_elapsed = date_diff(getdate(last_remit), month_end)
		else:
			days_elapsed = date_diff(_today, month_end)

		# Risk level color-coding
		if outstanding <= 0:
			risk = _("Green - Paid")
		elif days_elapsed <= 30:
			risk = _("Green - < 30 days")
		elif days_elapsed <= 60:
			risk = _("Yellow - 31-60 days")
		elif days_elapsed <= 90:
			risk = _("Orange - 61-90 days")
		else:
			risk = _("Red - > 90 days (POESSA Debit Risk)")

		data.append({
			"month": mk,
			"month_end": month_end,
			"emp_pension_total": emp_pension,
			"org_pension_total": org_pension,
			"total_pension": flt(total_pension, 2),
			"amount_remitted": flt(remitted, 2),
			"outstanding": flt(outstanding, 2),
			"last_remittance_date": last_remit or "",
			"days_elapsed": max(days_elapsed, 0),
			"risk_level": risk
		})

	return columns, data
