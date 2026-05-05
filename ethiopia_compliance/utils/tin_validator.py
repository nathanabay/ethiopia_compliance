"""
Ethiopian TIN (Tax Identification Number) Validator

Ethiopian TIN Format:
- Individual TINs: 10 digits (e.g., 0012345678)
- Company TINs: 10 digits (e.g., 0001234567)
- VAT TINs: Sometimes prefixed with country code

This module provides validation functions for Ethiopian TINs.

Proclamation No. 979/2016 Art. 97 as amended by Proclamation No. 1395/2017:
- Missing or invalid supplier TIN triggers the punitive 30% WHT rate.

Check-Digit Validation (P3-21 — pending IRS publication):
- Ethiopian IRS has not published an official check-digit algorithm.
- A formal check-digit scheme (per IRS directive) should be implemented here
  once published. The stub `_validate_check_digit()` raises NotImplementedError
  and should be updated when the algorithm is available.
  Do NOT use a generic algorithm (e.g., Luhn) as a substitute — it may reject
  valid TINs and accept invalid ones.
"""

import frappe
import re
from frappe import _


def validate_tin(tin_number):
    """
    Main TIN validation function

    Args:
        tin_number (str): The TIN to validate

    Returns:
        dict: {
            'valid': bool,
            'message': str,
            'type': str (Individual/Company/Unknown)
        }
    """
    if not tin_number:
        return {
            'valid': False,
            'message': 'TIN number is required',
            'type': 'Unknown'
        }

    # Remove any spaces or dashes
    tin_clean = re.sub(r'[\s\-]', '', str(tin_number))

    # Check if it's all digits
    if not tin_clean.isdigit():
        return {
            'valid': False,
            'message': 'TIN must contain only digits',
            'type': 'Unknown'
        }

    # Check length
    if len(tin_clean) != 10:
        return {
            'valid': False,
            'message': f'TIN must be exactly 10 digits (found {len(tin_clean)})',
            'type': 'Unknown'
        }

    # Determine type and validate
    if tin_clean.startswith('0'):
        result = validate_individual_tin(tin_clean)
    else:
        result = validate_company_tin(tin_clean)

    # Check-digit validation (pending IRS publication — see module docstring)
    if result.get('valid'):
        check_result = _validate_check_digit(tin_clean)
        if not check_result.get('valid'):
            return check_result

    return result


def _validate_check_digit(tin_number):
    """Validate TIN check digit per Ethiopian IRS directive.

    This function is a placeholder. Ethiopian IRS has not published an official
    check-digit algorithm. Once published, update this function with the
    official algorithm. Do NOT substitute a generic algorithm (Luhn, Mod 97,
    etc.) as it will incorrectly reject valid TINs.
    """
    # TODO (P3-21): Implement once Ethiopian IRS publishes check-digit scheme
    # Expected signature: _validate_check_digit(tin_number: str) -> dict
    #
    # Until then, all 10-digit numeric TINs are accepted structurally.
    # The punitive WHT rate still applies to TINs that are missing or
    # structurally invalid (wrong length, non-numeric).
    return {'valid': True, 'message': 'Check digit validation pending IRS publication'}


def validate_individual_tin(tin_number):
    """Validate individual TIN format (starts with 0)"""
    if len(tin_number) != 10:
        return {
            'valid': False,
            'message': 'Individual TIN must be 10 digits',
            'type': 'Individual'
        }

    if not tin_number.startswith('0'):
        return {
            'valid': False,
            'message': 'Individual TIN typically starts with 0',
            'type': 'Individual'
        }

    return {
        'valid': True,
        'message': 'Valid Individual TIN',
        'type': 'Individual'
    }


def validate_company_tin(tin_number):
    """Validate company TIN format"""
    if len(tin_number) != 10:
        return {
            'valid': False,
            'message': 'Company TIN must be 10 digits',
            'type': 'Company'
        }

    return {
        'valid': True,
        'message': 'Valid Company TIN',
        'type': 'Company'
    }


@frappe.whitelist(methods=["POST"], xss_safe=True)
def validate_tin_api(tin_number: str) -> dict:
    """API endpoint for TIN validation (called from client-side JS)"""
    frappe.only_for(["Accounts Manager", "Accounts User", "System Manager"])
    tin_number = str(tin_number).strip()
    return validate_tin(tin_number)


@frappe.whitelist(methods=["POST"], xss_safe=True)
def bulk_validate_tins(tin_list) -> list:
    """Validate multiple TINs at once (max 500)"""
    frappe.only_for(["Accounts Manager", "Accounts User", "System Manager"])
    import json

    if isinstance(tin_list, str):
        tin_list = json.loads(tin_list)

    if not isinstance(tin_list, list):
        frappe.throw(_("tin_list must be a JSON array"))

    if len(tin_list) > 500:
        frappe.throw(_("Maximum 500 TINs can be validated at once"))

    return [dict(validate_tin(tin), tin=tin) for tin in tin_list]


def check_duplicate_tin(doctype, tin_number, exclude_name=None):
    """
    Check if TIN already exists in database

    Args:
        doctype (str): DocType to check (Supplier/Customer/Employee)
        tin_number (str): TIN to check
        exclude_name (str): Name to exclude from check (for updates)

    Returns:
        dict: {'duplicate': bool, 'existing_record': str or None}
    """
    if not tin_number:
        return {'duplicate': False, 'existing_record': None}

    field_map = {
        'Supplier': 'tax_id',
        'Customer': 'tax_id',
        'Employee': 'tax_id',
        'Company': 'tax_id'
    }

    field_name = field_map.get(doctype)
    if not field_name:
        return {'duplicate': False, 'existing_record': None}

    filters = [[doctype, field_name, '=', tin_number]]
    if exclude_name:
        filters.append([doctype, 'name', '!=', exclude_name])

    existing = frappe.db.get_value(doctype, filters, 'name')

    return {
        'duplicate': bool(existing),
        'existing_record': existing
    }


def validate_party_tin(doc, method):
    """Strict TIN format validation for Supplier and Customer party masters.

    Ensures tax_id is exactly 10 numeric digits. Hooked to Supplier and
    Customer validate events via hooks.py.

    Args:
        doc: Supplier or Customer document
        method: Hook method name (unused)
    """
    if not doc.tax_id:
        return

    tin_clean = str(doc.tax_id).replace("-", "").replace(" ", "").strip()

    if not tin_clean:
        return

    if not tin_clean.isdigit():
        frappe.throw(
            _("TIN must contain only digits. Found: {0}").format(doc.tax_id)
        )

    if len(tin_clean) != 10:
        frappe.throw(
            _("TIN must be exactly 10 digits. Input has {0} digits. "
              "Please verify the Tax Identification Number for {1}.").format(
                len(tin_clean), doc.name
            )
        )

    # Clean and normalize
    doc.tax_id = tin_clean


def is_supplier_tin_valid(supplier_name):
    """Check if a supplier has a valid (structurally correct) TIN.

    Used by WHT logic to determine whether to apply the punitive 30% rate.

    Args:
        supplier_name (str): Supplier name

    Returns:
        bool: True if valid, False if missing or invalid
    """
    if not supplier_name:
        return False

    tin = frappe.db.get_value("Supplier", supplier_name, "tax_id")
    if not tin:
        return False

    result = validate_tin(str(tin).strip())
    return result.get('valid', False)


def count_unvalidated_tins():
    """Number card: count suppliers that are WHT-eligible but have no valid TIN.

    Returns:
        int: count of suppliers needing TIN validation
    """
    try:
        return frappe.db.count("Supplier", {
            "custom_wht_eligible": 1,
            "tax_id": ["in", ["", None]]
        })
    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Ethiopia Compliance Error: count_unvalidated_tins"
        )
        return 0