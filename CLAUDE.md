# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ethiopia Compliance is a Frappe/ERPNext application that implements Ethiopian tax and labor regulatory requirements including WHT (Withholding Tax), TIN validation, VAT reporting, pension compliance, and fiscal device integration.



## Common Commands

```bash
# Run a single test
cd /home/frappe/frappe-bench/apps/ethiopia_compliance
bench --site [site-name] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_wht_logic

# Run all tests for the app
bench --site [site-name] run-tests --app ethiopia_compliance

# Install the app
bench get-app /path/to/repo --branch main
bench --site [site-name] install-app ethiopia_compliance

# Enable pre-commit
cd apps/ethiopia_compliance && pre-commit install
```

## Architecture

### Core Modules

| Module | Purpose |
|--------|---------|
| `accounts/wht_logic.py` | WHT application on Purchase Invoices — applies 3% standard or 30% punitive rate based on supplier TIN validity |
| `accounts/wht_certificate_logic.py` | Auto-generates WHT certificates on invoice/payment submission |
| `accounts/invoice_logic.py` | Sales Invoice validation (fiscal device registration, TIN checks) |
| `accounts/payment_logic.py` | Cash transaction limits (50k ETB ceiling), journal entry controls |
| `accounts/po_logic.py` | Supplier TIN warnings on Purchase Orders |
| `utils/tin_validator.py` | TIN format validation (10-digit), API endpoints for bulk validation |
| `hr/employee_logic.py` | Employee validation hooks |
| `tasks/compliance_alerts.py` | Daily/weekly/monthly scheduled alerts for pension and tax deadlines |
| `overrides/leave_allocation.py` | Daily leave balance updates |
| `integrations/fiscal_device.py` | Fiscal device sales registration |

### Hooks (hooks.py)

The app uses `doc_events` to hook into ERPNext documents:
- **Purchase Invoice**: `before_save` applies WHT; `on_submit` triggers WHT certificate creation
- **Sales Invoice**: `before_submit` registers with fiscal device and validates TIN
- **Payment Entry**: `validate` checks cash limits; `on_submit` creates WHT certificates
- **Journal Entry**: `validate` checks cash limits
- **Purchase Order**: `validate` warns if supplier TIN missing
- **Supplier/Customer**: `validate` enforces 10-digit TIN format
- **Employee**: `validate` runs employee validation

### Custom Fields

Custom fields are defined in `fixtures/` as JSON and loaded via `hooks.py` fixtures. The app uses `custom_` prefixed fields on standard ERPNext doctypes (e.g., `custom_supplier_tin`, `custom_wht_eligible`).

### Key Tax Concepts

- **WHT Thresholds** (Art. 97): Goods >20,000 ETB, Services >10,000 ETB
- **WHT Rates**: Standard 3%, Punitive 30% (missing/invalid supplier TIN)
- **Schedule A** (employment income): Progressive slabs from 0-35% based on monthly income
- **MAT** (Minimum Alternative Tax): 2.5% of gross sales when net profit tax < 2.5% of gross
- **Cash Limit**: 50,000 ETB ceiling for cash payments (Article 81/1395/2017)

### Reports

Reports are in `report/` directory. All implement the standard `execute(filters)` function returning columns and data.

## Development Notes

- **Frappe TestCase**: Tests extend `frappe.tests.utils.FraseTestCase`
- **Compliance Setting**: Single doctype record ("Compliance Setting") stores all configurable rates and accounts
- **TIN Validation**: Strict 10-digit format; invalid/missing TIN triggers punitive WHT rate
- **Fixtures**: Custom fields, client scripts, server scripts, property setters, workflows, and fiscal year "2017 E.C." are loaded via fixtures
## AI Skills & specialized Context
- **Skills Directory**: All Frappe and ERPNext specific development skills are located in `./.claude/skills/`.
- **Instruction Priority**: Before implementing new DocTypes, Server Scripts, or Client Scripts, consult the corresponding `.md` file in the skills directory.
- **ORM Guidelines**: strictly adhere to the rules in `frappe-orm.md` and `syntax-server-scripts.md` (e.g., no raw SQL, use `frappe.get_all`).
- **Testing**: Use the patterns defined in `testing-backend.md` for all new test cases.
