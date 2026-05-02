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


# --- PAYE COMPUTATION ---

def compute_paye_tax(taxable_income):
	"""
	Compute Ethiopian PAYE (Pay As You Earn) income tax per Proclamation No. 1395/2025.

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
