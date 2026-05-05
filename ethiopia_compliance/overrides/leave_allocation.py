import frappe


def run_daily_leave_update():
	"""Scheduled daily task for leave allocation updates.

	Can be extended to handle Ethiopian public holidays,
	leave balance adjustments, or calendar sync.
	"""
	if not frappe.lock("run_daily_leave_update", timeout=60):
		return
	from erpnext.hr.doctype.leave_allocation.recalculate_leave_allocation import RecalculateLeaveAllocation

	try:
		RecalculateLeaveAllocation().run()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Ethiopia Compliance Error: run_daily_leave_update"
		)
	finally:
		frappe.unlock("run_daily_leave_update")
