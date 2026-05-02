import frappe
from frappe import _

CASH_LIMIT = 50000  # Proclamation No. 1395/2025 Art. 29


def validate_cash_limits(doc, method):
	"""Block cash payments exceeding 50,000 ETB.

	Hooked to Payment Entry validate via hooks.py.
	Proclamation No. 1395/2025 Article 29 prohibits cash transactions above 50,000 ETB.
	"""
	amount = doc.paid_amount or doc.base_paid_amount or 0
	if amount <= CASH_LIMIT:
		return

	mode_of_payment = doc.mode_of_payment
	if not mode_of_payment:
		return

	# Determine if this is a cash payment
	is_cash = False

	mop = frappe.get_cached_value("Mode of Payment", mode_of_payment, "type")
	if mop and mop.strip().lower() == "cash":
		is_cash = True
	elif not mop:
		# Fallback: check if mode_of_payment name implies cash
		if "cash" in str(mode_of_payment).lower():
			is_cash = True

	if is_cash:
		frappe.throw(
			_("Cash payments exceeding 50,000 ETB are prohibited under "
			  "Proclamation No. 1395/2025 Article 29. "
			  "Transaction amount: {0:,.2f} ETB").format(amount)
		)
