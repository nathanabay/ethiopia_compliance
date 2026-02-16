# TIN Validation Module
from ethiopia_compliance.utils.tin_validator import (
    validate_tin,
    validate_individual_tin,
    validate_company_tin,
    validate_tin_api,
    bulk_validate_tins,
    check_duplicate_tin
)

__all__ = [
    'validate_tin',
    'validate_individual_tin',
    'validate_company_tin',
    'validate_tin_api',
    'bulk_validate_tins',
    'check_duplicate_tin'
]
