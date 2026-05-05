# Ethiopia Compliance Utilities
from frappe import _
import frappe
from frappe.utils import getdate

# Re-export TIN validator functions
from ethiopia_compliance.utils.tin_validator import (
	validate_tin,
	validate_individual_tin,
	validate_company_tin,
	validate_tin_api,
	bulk_validate_tins,
	check_duplicate_tin
)

__all__ = [
	'get_ec_date',
	'get_gc_date',
	'get_calendar_settings',
	'compute_paye_tax',
	'validate_tin',
	'validate_individual_tin',
	'validate_company_tin',
	'validate_tin_api',
	'bulk_validate_tins',
	'check_duplicate_tin'
]


# --- ETHIOPIAN CALENDAR LOGIC ---

@frappe.whitelist(methods=["GET", "POST"], xss_safe=True)
def get_ec_date(date: str) -> str:
	"""API Endpoint: Convert Gregorian to Ethiopian"""
	if not date:
		return ""

	cache_key = f"ethiopia_compliance:ec_date:{date}"
	cached = frappe.cache().get_value(cache_key)
	if cached is not None:
		return cached

	try:
		from ethiopian_date import EthiopianDateConverter

		d = getdate(date)
		ec = EthiopianDateConverter.to_ethiopian(d.year, d.month, d.day)

		if isinstance(ec, (tuple, list)):
			result = f"{ec[2]:02d}-{ec[1]:02d}-{ec[0]}"
		elif hasattr(ec, 'day'):
			result = f"{ec.day:02d}-{ec.month:02d}-{ec.year}"
		else:
			result = str(ec)

		frappe.cache().set_value(cache_key, result, expires_in_sec=86400)
		return result

	except ImportError:
		frappe.throw(_("ethiopian_date library is not installed. Install with: pip install ethiopian-date"))
	except Exception:
		frappe.log_error(title="EC Date Conversion Error")
		return ""


@frappe.whitelist(methods=["GET", "POST"], xss_safe=True)
def get_gc_date(ethiopian_date: str) -> str:
	"""API Endpoint: Convert Ethiopian DD-MM-YYYY to Gregorian"""
	if not ethiopian_date:
		return ""

	cache_key = f"ethiopia_compliance:gc_date:{ethiopian_date}"
	cached = frappe.cache().get_value(cache_key)
	if cached is not None:
		return cached

	try:
		from ethiopian_date import EthiopianDateConverter

		parts = ethiopian_date.split('-')
		if len(parts) != 3:
			return ""

		d, m, y = int(parts[0]), int(parts[1]), int(parts[2])

		if not (1 <= m <= 13 and 1 <= d <= 30):
			return ""

		gc = EthiopianDateConverter.to_gregorian(y, m, d)

		if isinstance(gc, (tuple, list)):
			result = f"{gc[0]}-{gc[1]:02d}-{gc[2]:02d}"
		elif hasattr(gc, 'day'):
			result = f"{gc.year}-{gc.month:02d}-{gc.day:02d}"
		else:
			result = str(gc)

		frappe.cache().set_value(cache_key, result, expires_in_sec=86400)
		return result

	except (ValueError, IndexError):
		return ""
	except Exception:
		frappe.log_error(title="GC Date Conversion Error")
		return ""


@frappe.whitelist(methods=["GET", "POST"], xss_safe=True)
def get_calendar_settings() -> dict:
	"""API Endpoint: Get Ethiopian calendar settings from Compliance Setting"""
	try:
		settings = frappe.get_cached_doc("Compliance Setting")
		return {
			"enable_ethiopian_calendar": settings.get("enable_ethiopian_calendar") or 0
		}
	except Exception:
		return {"enable_ethiopian_calendar": 1}


def apply_ethiopian_date_filters(filters):
	"""Apply Ethiopian calendar date conversion to report filters in-place.

	Converts from_date and to_date from DD-MM-YYYY Ethiopian format to
	Gregorian YYYY-MM-DD format when use_ethiopian_calendar is set.

	Use in report execute() functions to replace inline filter conversion code.
	Cross-DB compatible — no MariaDB/PostgreSQL date functions.

	Args:
		filters (dict): Report filters dict (modified in-place)

	Example:
		apply_ethiopian_date_filters(filters)
		# Now filters["from_date"] and filters["to_date"] are Gregorian
	"""
	if not filters.get("use_ethiopian_calendar"):
		return

	for key in ("from_date", "to_date"):
		if filters.get(key):
			parts = str(filters[key]).split("-")
			if len(parts) == 3:
				# Convert from DD-MM-YYYY to YYYY-MM-DD for get_gc_date
				eth_date = f"{parts[2]}-{parts[1]}-{parts[0]}"
				gc_date = get_gc_date(eth_date)
				if gc_date:
					filters[key] = gc_date


# --- PAYE COMPUTATION ---

def compute_paye_tax(taxable_income):
	"""
	Compute Ethiopian PAYE (Pay As You Earn) income tax per Proclamation No. 1395/2025.

	Uses ERPNext Income Tax Slabs dynamically. Falls back to hardcoded brackets
	if no slab is found in the database.

	Brackets (effective July 2025):
		0 - 2,000:     0%
		2,001 - 4,000:  15%  (cumulative: 300)
		4,001 - 7,000:  20%  (cumulative: 900)
		7,001 - 10,000: 25%  (cumulative: 1,650)
		10,001 - 14,000: 30%  (cumulative: 2,850)
		Over 14,000:    35%

	Args:
		taxable_income (float): Monthly taxable income (gross pay - employee pension)

	Returns:
		float: Computed PAYE tax amount
	"""
	from frappe.utils import flt

	taxable = flt(taxable_income)

	if taxable <= 0:
		return 0.0

	# Attempt to fetch active ERPNext Income Tax Slab
	slabs = _fetch_income_tax_slabs()

	if slabs:
		return _compute_from_slabs(taxable, slabs)

	# Fallback: hardcoded brackets per Proclamation No. 1395/2025
	return _compute_fallback(taxable)


def _fetch_income_tax_slabs():
	"""Fetch active Income Tax Slab details from ERPNext, sorted by from_amount."""
	try:
		# Fetch the slab with the most recent effective_from date
		slab_name = frappe.db.get_value(
			"Income Tax Slab",
			{},
			"name",
			order_by="effective_from desc"
		)
		if not slab_name:
			return None

		details = frappe.db.get_all(
			"Income Tax Slab Detail",
			filters={"parent": slab_name},
			fields=["from_amount", "to_amount", "percent_deduction"],
			order_by="from_amount asc"
		)
		if not details:
			return None

		return [
			{
				"from_amount": flt(d.from_amount),
				"to_amount": flt(d.to_amount),
				"rate": flt(d.percent_deduction) / 100.0
			}
			for d in details
		]
	except Exception:
		return None


def _compute_from_slabs(taxable, slabs):
	"""Compute progressive PAYE tax from ERPNext slab definitions."""
	from frappe.utils import flt

	tax = 0.0

	for slab in slabs:
		from_amt = slab["from_amount"]
		to_amt = slab["to_amount"]
		rate = slab["rate"]

		if to_amt <= 0:
			# Unbounded top bracket
			if taxable >= from_amt:
				bracket_width = taxable - from_amt + 1
				tax += bracket_width * rate
			break

		if taxable > to_amt:
			# Full bracket applies
			bracket_width = to_amt - from_amt + 1
			tax += bracket_width * rate
		else:
			# Taxable falls within this bracket
			bracket_width = taxable - from_amt + 1
			tax += bracket_width * rate
			break

	return flt(tax, 2)


def _compute_fallback(taxable):
	"""Hardcoded fallback: PAYE brackets per Proclamation No. 1395/2025."""
	from frappe.utils import flt

	brackets = [
		(2000, 0.00, 0),
		(4000, 0.15, 0),
		(7000, 0.20, 300),
		(10000, 0.25, 900),
		(14000, 0.30, 1650),
	]

	prev_upper = 0
	for limit, rate, cumulative in brackets:
		if taxable <= limit:
			return flt(cumulative + (taxable - prev_upper) * rate, 2)
		prev_upper = limit

	# Top bracket: over 14,000 at 35%
	return flt(2850 + (taxable - 14000) * 0.35, 2)


# --- TIN VALIDATION HELPERS ---

def get_tin_status(tin_number):
	"""
	Get a simple TIN status string for use in report columns.

	Args:
		tin_number (str): TIN to check

	Returns:
		str: "Valid", "Missing", or "Invalid Format"
	"""
	if not tin_number or str(tin_number).strip() == "":
		return _("Missing")

	tin_clean = str(tin_number).strip().replace(" ", "").replace("-", "")

	if not tin_clean.isdigit():
		return _("Invalid Format")

	if len(tin_clean) != 10:
		return _("Invalid Format")

	return _("Valid")
