# Ethiopia Compliance Dashboard Extension Design

## Overview
Extend the existing `compliance_dashboard` page to add stat cards and charts providing a business overview alongside the existing tax-focused functionality.

## Layout

```
┌─────────────────────────────────────────────────────────┐
│ [Period Selector: This Month / Last Month / etc.]       │
├──────────┬──────────┬──────────┬──────────────────────────┤
│ Companies│ Fiscal   │Employees │ Active                    │
│   XX     │ Devices  │   XX     │ Contracts  XX            │
│          │   XX     │          │                           │
├──────────┴──────────┴──────────┴──────────────────────────┤
│  Revenue Chart        │  Expenses Chart                     │
│                      │                                     │
├──────────────────────┴───────────────────────────────────┤
│  Cash Flow Chart    │  Taxes Chart                         │
│                     │                                      │
├──────────────────────────────────────────────────────────┤
│  [Existing: Tax Summary | Recent Docs | Compliance]       │
└──────────────────────────────────────────────────────────┘
```

## New Stat Cards

| Card | Data Source | API |
|------|-------------|-----|
| Total Companies | `tabCompany` where country = Ethiopia | `get_overview_stats()` |
| Fiscal Devices | `tabFiscal Device` with status='Active' | `get_overview_stats()` |
| Employees | `tabEmployee` linked to company | `get_overview_stats()` |
| Active Contracts | `tabContract` with status='Active' | `get_overview_stats()` |

## New Charts

| Chart | Type | Data Source |
|-------|------|-------------|
| Revenue | Line/Bar | Monthly `Sales Invoice` totals (docstatus=1) |
| Expenses | Line/Bar | Monthly `Purchase Invoice` totals (docstatus=1) |
| Cash Flow | Line | Net of Revenue - Expenses per month |
| Taxes | Bar | WHT, VAT, TOT collected by month |

Chart data API: `get_chart_data(period)` returning monthly breakdown.

## Period Options
- This Month (default)
- Last Month
- Last Quarter
- This Year
- Custom date range

## API Design

### `get_overview_stats(company)` - New
Returns dict:
```python
{
    'total_companies': int,
    'fiscal_devices': int,
    'employees': int,
    'active_contracts': int
}
```

### `get_chart_data(period, from_date, to_date)` - New
Returns dict:
```python
{
    'revenue': [{'month': 'Jan', 'amount': 1000}, ...],
    'expenses': [{'month': 'Jan', 'amount': 800}, ...],
    'cash_flow': [{'month': 'Jan', 'amount': 200}, ...],
    'taxes': {
        'wht': [...],
        'vat': [...],
        'tot': [...]
    }
}
```

### `get_dashboard_data(period, from_date, to_date)` - Modified
Extend existing endpoint to include:
```python
{
    # existing fields...
    'overview_stats': get_overview_stats(company),
    'chart_data': get_chart_data(period, from_date, to_date)
}
```

## Files to Modify
1. `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py` - Add new functions, modify `get_dashboard_data`
2. `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js` - Add chart rendering

## Files to Create
1. `ethiopia_compliance/page/compliance_dashboard/overview_stats.py` - Stat card data (optional, for organization)

## Implementation Order
1. Add `get_overview_stats()` to compliance_dashboard.py
2. Add `get_chart_data()` to compliance_dashboard.py
3. Update `get_dashboard_data()` to include new data
4. Update compliance_dashboard.js to render stat cards
5. Update compliance_dashboard.js to render charts
6. Update compliance_dashboard.json if needed (roles/permissions)
