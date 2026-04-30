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
	'validate_tin',
	'validate_individual_tin',
	'validate_company_tin',
	'validate_tin_api',
	'bulk_validate_tins',
	'check_duplicate_tin'
]


# --- ETHIOPIAN CALENDAR LOGIC ---

@frappe.whitelist(methods=["GET"], xss_safe=True)
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


@frappe.whitelist(methods=["GET"], xss_safe=True)
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
