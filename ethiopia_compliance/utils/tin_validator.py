"""
Ethiopian TIN (Tax Identification Number) Validator

Ethiopian TIN Format:
- Individual TINs: 10 digits (e.g., 0012345678)
- Company TINs: 10 digits (e.g., 0001234567)
- VAT TINs: Sometimes prefixed with country code

This module provides validation functions for Ethiopian TINs.
"""

import frappe
import re


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
        return validate_individual_tin(tin_clean)
    else:
        return validate_company_tin(tin_clean)


def validate_individual_tin(tin_number):
    """
    Validate individual TIN format
    
    Individual TINs typically start with 0
    
    Args:
        tin_number (str): 10-digit TIN
        
    Returns:
        dict: Validation result
    """
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
    """
    Validate company TIN format
    
    Company TINs have specific format rules
    
    Args:
        tin_number (str): 10-digit TIN
        
    Returns:
        dict: Validation result
    """
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


@frappe.whitelist()
def validate_tin_api(tin_number):
    """
    API endpoint for TIN validation
    Called from client-side JavaScript
    
    Args:
        tin_number (str): TIN to validate
        
    Returns:
        dict: Validation result
    """
    return validate_tin(tin_number)


@frappe.whitelist()
def bulk_validate_tins(tin_list):
    """
    Validate multiple TINs at once
    
    Args:
        tin_list (list): List of TIN numbers
        
    Returns:
        list: List of validation results
    """
    if isinstance(tin_list, str):
        import json
        tin_list = json.loads(tin_list)
    
    results = []
    for tin in tin_list:
        result = validate_tin(tin)
        result['tin'] = tin
        results.append(result)
    
    return results


def check_duplicate_tin(doctype, tin_number, exclude_name=None):
    """
    Check if TIN already exists in database
    
    Args:
        doctype (str): DocType to check (Supplier/Customer/Employee)
        tin_number (str): TIN to check
        exclude_name (str): Name to exclude from check (for updates)
        
    Returns:
        dict: {
            'duplicate': bool,
            'existing_record': str or None
        }
    """
    if not tin_number:
        return {'duplicate': False, 'existing_record': None}
    
    # Determine field name based on doctype
    field_map = {
        'Supplier': 'tax_id',
        'Customer': 'tax_id',
        'Employee': 'tax_id',
        'Company': 'tax_id'
    }
    
    field_name = field_map.get(doctype)
    if not field_name:
        return {'duplicate': False, 'existing_record': None}
    
    filters = {field_name: tin_number}
    if exclude_name:
        filters['name'] = ['!=', exclude_name]
    
    existing = frappe.db.get_value(doctype, filters, 'name')
    
    return {
        'duplicate': bool(existing),
        'existing_record': existing
    }
