import frappe
from frappe import _
from frappe.utils import flt

CASH_LIMIT = 50000  # Proclamation No. 1395/2017 Art. 29 / Art. 81


def validate_cash_limits(doc, method):
    """Block cash receipts/payments exceeding 50,000 ETB per transaction.

    Hooked to Payment Entry and Journal Entry validate events via hooks.py.
    Proclamation No. 1395/2017 Article 29 (and Article 81 for payments) prohibits
    cash transactions above 50,000 ETB in aggregate to the same person per day.
    """
    if doc.doctype == "Payment Entry":
        _validate_payment_entry_cash(doc)
    elif doc.doctype == "Journal Entry":
        _validate_journal_entry_cash(doc)


def _get_cash_limit():
    """Fetch cash_limit from Compliance Setting; fallback to 50000."""
    try:
        settings = frappe.get_cached_doc("Compliance Setting")
        return flt(settings.cash_limit) or 50000
    except Exception:
        return 50000


def _is_cash_mode(mode_of_payment):
    """Return True if the mode_of_payment is cash."""
    if not mode_of_payment:
        return False
    mop_type = frappe.get_cached_value("Mode of Payment", mode_of_payment, "type")
    if mop_type and mop_type.strip().lower() == "cash":
        return True
    if "cash" in str(mode_of_payment).lower():
        return True
    return False


def _validate_payment_entry_cash(doc):
    """Validate a Payment Entry for cash limit compliance."""
    if doc.payment_type not in ("Receive", "Pay"):
        return

    amount = flt(doc.paid_amount or doc.base_paid_amount or 0)
    if amount <= 0:
        return

    cash_limit = _get_cash_limit()
    if amount <= cash_limit:
        return

    if not _is_cash_mode(doc.mode_of_payment):
        return

    frappe.throw(
        _("Cash transactions exceeding {0} ETB are prohibited under "
          "Proclamation No. 1395/2017 Article 29/81. "
          "This transaction is {1:,.2f} ETB. "
          "Please use Bank Transfer, CPO, or Cheque.").format(
            cash_limit, amount
        ),
        title=_("Cash Limit Exceeded")
    )


def _validate_journal_entry_cash(doc):
    """Validate a Journal Entry for cash account payments exceeding limit."""
    if doc.docstatus != 0:
        return

    cash_limit = _get_cash_limit()

    for account_entry in doc.accounts:
        if account_entry.debit > 0:
            amount = flt(account_entry.debit)
        elif account_entry.credit > 0:
            amount = flt(account_entry.credit)
        else:
            continue

        if amount <= cash_limit:
            continue

        is_cash = _is_cash_account(account_entry.account)
        if not is_cash:
            continue

        # Determine party info for error message
        party_info = ""
        if account_entry.party:
            party_info = f" for party {account_entry.party}"
        elif doc.party_name:
            party_info = f" for party {doc.party_name}"

        frappe.throw(
            _("Cash transactions exceeding {0} ETB are prohibited under "
              "Proclamation No. 1395/2017 Article 29/81. "
              "Journal Entry '{1}' has a cash entry of {2:,.2f} ETB{3}. "
              "Please use Bank Transfer, CPO, or Cheque.").format(
                cash_limit, doc.name, amount, party_info
            ),
            title=_("Cash Limit Exceeded")
        )


def _is_cash_account(account):
    """Check if an account is a cash account by its account type or name."""
    if not account:
        return False
    account_type = frappe.get_cached_value("Account", account, "account_type")
    if account_type and account_type.strip().lower() == "cash":
        return True
    if "cash" in str(account).lower():
        return True
    return False


# ──────────────────────────────────────────
# Journal Entry on_submit cash enforcement
# ──────────────────────────────────────────

def validate_journal_entry_on_submit(doc, method):
    """Additional check on submit — race condition guard."""
    _validate_journal_entry_cash(doc)


def count_near_cash_limit():
    """Number card: count Payment Entries with cash mode and amount > 40,000 ETB
    (within 20% of the 50,000 limit — pending/draft state).

    Returns:
        int: count of at-risk cash transactions
    """
    try:
        cash_limit = _get_cash_limit()
        threshold = cash_limit * 0.80  # flag transactions at 80%+ of limit
        return frappe.db.count("Payment Entry", {
            "mode_of_payment": ["like", "%Cash%"],
            "paid_amount": [">=", threshold],
            "docstatus": 0
        })
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Ethiopia Compliance Error: count_near_cash_limit"
        )
        return 0