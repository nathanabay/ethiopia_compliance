# Compliance Alert System
# Scheduled tasks for pension tracking, tax deadlines, and email digests

import frappe
from frappe import _
from frappe.utils import flt, getdate, today, add_days, date_diff, nowdate, format_date
from frappe.utils import add_months as add_months_util
from datetime import date, timedelta
import calendar


# ──────────────────────────────────────────
# Pension Component Names
# ──────────────────────────────────────────
EMP_PENSION_COMPONENTS = {"Pension (Employee)", "Employee Pension", "Employee Pension (7%)"}
ORG_PENSION_COMPONENTS = {"Pension (Employer)", "Employer Pension", "Employer Pension (11%)"}


# ──────────────────────────────────────────
# Overdue Pension Check — POESSA 30-day rule
# ──────────────────────────────────────────

def check_overdue_pension():
	"""Daily scheduled task: detect overdue pension remittances.

	Compares total monthly pension liability (employee + employer portions)
	against Payment Entries made to POESSA accounts. If pension is overdue
	by 30+ days from month-end, creates a Notification Log for Accounts Manager.

	Wire to: scheduler_events.daily in hooks.py
	"""
	try:
		_today = getdate(today())

		# Get company
		company = frappe.defaults.get_user_default("Company")
		if not company:
			return

		# Look back 4 months — we only care about overdue, not current month
		cutoff = add_days(_today, -120)
		from_date_str = cutoff.strftime("%Y-%m-%d")
		today_str = _today.strftime("%Y-%m-%d")

		# 1. Aggregate pension liability from submitted salary slips by month
		pension_by_month = _get_monthly_pension_liability(company, from_date_str, today_str)
		if not pension_by_month:
			return

		# 2. Get remittances by month (POESSA-related Payment Entries)
		remittances_by_month = _get_monthly_pension_remittances(company, from_date_str)

		# 3. Compare and alert
		for month_key, liability in pension_by_month.items():
			month_end = getdate(liability["month_end"])
			days_since_month_end = date_diff(_today, month_end)

			# Only alert if 30+ days have passed
			if days_since_month_end < 30:
				continue

			total_due = liability["emp_pension"] + liability["org_pension"]
			total_remitted = flt(remittances_by_month.get(month_key, {}).get("amount", 0))
			outstanding = flt(total_due - total_remitted, 2)

			if outstanding <= 1.0:
				continue  # Settled within 1 ETB tolerance

			# Raise alert
			_create_pension_overdue_notification(
				company=company,
				month_key=month_key,
				month_end=month_end,
				total_due=total_due,
				outstanding=outstanding,
				days_overdue=days_since_month_end
			)
	except Exception:
		frappe.log_error(title="check_overdue_pension failed")
		_critical_alert_email(
			subject="CRITICAL: check_overdue_pension failed",
			body=f"<pre>{frappe.get_traceback()}</pre>"
		)


def _get_monthly_pension_liability(company, from_date, to_date):
	"""Aggregate employee + employer pension from Salary Slips by month."""
	# Build named placeholders for IN clauses
	emp_params = {}
	emp_placeholders = []
	for i, comp in enumerate(EMP_PENSION_COMPONENTS):
		key = f"ec{i}"
		emp_placeholders.append(f"%({key})s")
		emp_params[key] = comp

	org_params = {}
	org_placeholders = []
	for i, comp in enumerate(ORG_PENSION_COMPONENTS):
		key = f"oc{i}"
		org_placeholders.append(f"%({key})s")
		org_params[key] = comp

	values = {
		"company": company,
		"from_date": from_date,
		"to_date": to_date,
	}
	values.update(emp_params)
	values.update(org_params)

	slips = frappe.db.sql("""
		SELECT
			DATE_FORMAT(ss.end_date, '%%Y-%%m') as month_key,
			LAST_DAY(ss.end_date) as month_end,
			sd.salary_component,
			SUM(sd.amount) as total_amount
		FROM `tabSalary Slip` ss
		JOIN `tabSalary Detail` sd ON sd.parent = ss.name
		WHERE ss.company = %(company)s
			AND ss.docstatus = 1
			AND ss.start_date >= %(from_date)s
			AND ss.end_date <= %(to_date)s
			AND (
				sd.salary_component IN ({emp_in})
				OR sd.salary_component IN ({org_in})
			)
		GROUP BY month_key, sd.salary_component
	""".format(
		emp_in=",".join(emp_placeholders),
		org_in=",".join(org_placeholders)
	), values, as_dict=True)

	pension_by_month = {}
	for row in slips:
		mk = row.month_key
		if mk not in pension_by_month:
			pension_by_month[mk] = {
				"month_end": row.month_end,
				"emp_pension": 0.0,
				"org_pension": 0.0
			}
		if row.salary_component in EMP_PENSION_COMPONENTS:
			pension_by_month[mk]["emp_pension"] += flt(row.total_amount)
		elif row.salary_component in ORG_PENSION_COMPONENTS:
			pension_by_month[mk]["org_pension"] += flt(row.total_amount)

	return pension_by_month


def _get_monthly_pension_remittances(company, from_date):
	"""Aggregate Payment Entries to POESSA by month."""
	remittances = frappe.db.sql("""
		SELECT
			DATE_FORMAT(pe.posting_date, '%%Y-%%m') as month_key,
			SUM(pe.paid_amount) as total_amount
		FROM `tabPayment Entry` pe
		WHERE pe.company = %(company)s
			AND pe.docstatus = 1
			AND pe.payment_type = 'Pay'
			AND pe.posting_date >= %(from_date)s
			AND (
				pe.paid_to LIKE %(poessa)s
				OR pe.party LIKE %(poessa)s
				OR pe.paid_to_account_head LIKE %(poessa)s
			)
		GROUP BY month_key
	""", {
		"company": company,
		"from_date": from_date,
		"poessa": "%%POESSA%%"
	}, as_dict=True)

	return {r.month_key: {"amount": flt(r.total_amount)} for r in remittances}


def _create_pension_overdue_notification(company, month_key, month_end, total_due, outstanding, days_overdue):
	"""Create or update a Notification Log for overdue pension."""
	subject = _("POESSA Pension Remittance Overdue — {0}").format(month_key)
	doc_name = f"POESSA-OVERDUE-{month_key}"

	existing = frappe.db.exists("Notification Log", {
		"subject": subject,
		"for_user": "Administrator"
	})

	if existing:
		return  # Already notified

	email_content = _("""
		<h3>Pension Remittance Overdue — POESSA Risk</h3>
		<p><strong>Company:</strong> {company}</p>
		<p><strong>Payroll Month:</strong> {month_key} (ended {month_end})</p>
		<p><strong>Total Pension Due:</strong> {total_due:,.2f} ETB</p>
		<p><strong>Outstanding:</strong> {outstanding:,.2f} ETB</p>
		<p><strong>Days Overdue:</strong> {days_overdue} days</p>
		<hr>
		<p style="color: red;"><strong>WARNING:</strong> Under the POESSA regulation,
		pension is due within 30 days of the month end. Failure to remit may result
		in direct bank debit by the pension authority.</p>
		<p>Please process the outstanding payment immediately to avoid penalties.</p>
	""").format(
		company=company,
		month_key=month_key,
		month_end=format_date(month_end),
		total_due=total_due,
		outstanding=outstanding,
		days_overdue=days_overdue
	)

	# Send to Accounts Managers
	notify_users_with_role("Accounts Manager", subject, email_content)
	notify_users_with_role("System Manager", subject, email_content)


# ──────────────────────────────────────────
# Email helpers
# ──────────────────────────────────────────

def _critical_alert_email(subject, body):
	"""Send a critical alert email to the engineering team when a scheduler task fails.

	Delivers to Andualem and Selamawit so the team is immediately aware of
	background task failures that could indicate data or compliance risk.
	"""
	# Default recipients — replace with actual team emails
	recipients = ["andu@bespo.et", "selam@bespo.et"]
	try:
		frappe.sendmail(
			recipients=recipients,
			subject=subject,
			message=body,
			priority="high"
		)
	except Exception:
		frappe.log_error(title=f"Failed to send critical alert: {subject}")


def notify_users_with_role(role, subject, message):
	"""Send notification to all users with a given role.

	Note: Notification Log inserts use ignore_permissions=True because this
	function is called from scheduler (background) tasks where the system
	acts as an actor rather than a specific user session. The notification
	purpose is administrative alert delivery (not data access), so the
	permission bypass is intentional and scoped to Notification Log creation.
	"""
	users = frappe.db.get_all(
		"Has Role",
		filters={"role": role, "parenttype": "User"},
		fields=["parent"]
	)

	for user_row in users:
		try:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": user_row.parent,
				"type": "Alert",
				"email_content": message,
				"document_type": "Company"
			}).insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"Pension Alert — {role}")


# ──────────────────────────────────────────
# Tax Deadline Digest — Ethiopian calendar
# ──────────────────────────────────────────

def send_tax_deadline_digest():
	"""Weekly scheduled task: build upcoming tax deadline summary.

	Calculates Ethiopian calendar deadlines for:
	- WHT Certificates: 15th of next month
	- VAT / PAYE / Pension: 30th of next month

	Sends an HTML email digest to Accounts Manager.
	"""
	try:
		_today = getdate(today())
		company = frappe.defaults.get_user_default("Company") or _("All Companies")

		# Build deadline entries
		deadlines = _compute_upcoming_deadlines(_today)

		# Only send if we're within 7 days of any deadline
		urgent = [d for d in deadlines if d["urgency"] in ("overdue", "due_soon")]
		if not urgent:
			return

		html = _build_deadline_email(company, deadlines, _today)
		subject = _("Ethiopian Tax Deadline Digest — {0}").format(format_date(_today))

		notify_users_with_role("Accounts Manager", subject, html)
		notify_users_with_role("System Manager", subject, html)
	except Exception:
		frappe.log_error(title="send_tax_deadline_digest failed")
		_critical_alert_email(
			subject="CRITICAL: send_tax_deadline_digest failed",
			body=f"<pre>{frappe.get_traceback()}</pre>"
		)


def _compute_upcoming_deadlines(today_date):
	"""Compute the next set of tax deadlines with urgency classification."""
	year = today_date.year
	month = today_date.month
	day = today_date.day

	# Deadlines: label, day, month_offset
	deadlines_config = [
		(_("WHT Certificate Due"), 15, 1),
		(_("VAT Return Due"), 30, 1),
		(_("PAYE Declaration Due"), 30, 1),
		(_("Pension Remittance Due"), 30, 1),
	]

	deadlines = []
	for label, due_day, month_offset in deadlines_config:
		due_year = year
		due_month = month + month_offset
		if due_month > 12:
			due_month -= 12
			due_year += 1

		# Use last day of month if due_day > days in month
		last_day = calendar.monthrange(due_year, due_month)[1]
		actual_due = min(due_day, last_day)
		due_date = date(due_year, due_month, actual_due)

		days_remaining = date_diff(due_date, today_date)

		if days_remaining < 0:
			urgency = "overdue"
		elif days_remaining <= 5:
			urgency = "due_soon"
		elif days_remaining <= 14:
			urgency = "upcoming"
		else:
			urgency = "future"

		deadlines.append({
			"label": label,
			"due_date": str(due_date),
			"days_remaining": days_remaining,
			"urgency": urgency
		})

	return deadlines


def _build_deadline_email(company, deadlines, today_date):
	"""Build HTML email body for tax deadline digest."""
	color_map = {
		"overdue": "red",
		"due_soon": "#ff8c00",
		"upcoming": "#1e90ff",
		"future": "green"
	}

	rows = ""
	for d in deadlines:
		color = color_map.get(d["urgency"], "black")
		if d["days_remaining"] < 0:
			status = _("OVERDUE — {0} days ago").format(abs(d["days_remaining"]))
		elif d["days_remaining"] == 0:
			status = _("DUE TODAY")
		else:
			status = _("Due in {0} days").format(d["days_remaining"])
		rows += f"""
			<tr>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{d['label']}</td>
				<td style="padding: 8px; border-bottom: 1px solid #eee;">{format_date(d['due_date'])}</td>
				<td style="padding: 8px; border-bottom: 1px solid #eee; color: {color}; font-weight: bold;">{status}</td>
			</tr>"""

	return _("""
		<h2>Tax Compliance Deadline Digest</h2>
		<p><strong>Company:</strong> {company}</p>
		<p><strong>As of:</strong> {today}</p>

		<h3>Upcoming Filing Deadlines</h3>
		<table style="width: 100%%; border-collapse: collapse;">
			<thead>
				<tr style="background-color: #f5f5f5;">
					<th style="padding: 8px; text-align: left;">Obligation</th>
					<th style="padding: 8px; text-align: left;">Due Date</th>
					<th style="padding: 8px; text-align: left;">Status</th>
				</tr>
			</thead>
			<tbody>
				{rows}
			</tbody>
		</table>

		<hr>
		<p style="color: #666; font-size: 12px;">
			Deadlines are based on Ethiopian Ministry of Revenues requirements.<br>
			This digest was auto-generated by the Ethiopia Compliance system.
		</p>
	""").format(
		company=company,
		today=format_date(today_date),
		rows=rows
	)


# ──────────────────────────────────────────
# Shared helper for dashboard
# ──────────────────────────────────────────

def get_tax_calendar():
	"""Return upcoming deadlines with urgency — used by dashboard widget."""
	_today = getdate(today())
	return _compute_upcoming_deadlines(_today)
