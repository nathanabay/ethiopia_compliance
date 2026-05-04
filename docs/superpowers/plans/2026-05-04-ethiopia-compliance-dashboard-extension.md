# Ethiopia Compliance Dashboard Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stat cards and charts to the compliance dashboard providing a business overview alongside existing tax-focused functionality.

**Architecture:** Extend the existing `compliance_dashboard.py` with new data functions and update `compliance_dashboard.js` to render stat cards and Chart.js-based charts. The backend returns structured data; the frontend renders the UI.

**Tech Stack:** Frappe Framework, Chart.js (via frappe.chart), Python/JS

---

## File Inventory

| File | Action |
|------|--------|
| `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py` | Modify - add new data functions |
| `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js` | Modify - add stat cards and charts |
| `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.json` | No changes needed (already has roles) |

---

## Task 1: Add `get_overview_stats()` Function

**Files:**
- Modify: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py:210-232` (after `get_compliance_status`)

- [ ] **Step 1: Write test for get_overview_stats**

```python
# In tests file - create if not exists
# ethiopia_compliance/accounts/tests/test_dashboard.py

def test_get_overview_stats():
    """Test that overview stats returns expected structure"""
    from ethiopia_compliance.page.compliance_dashboard.compliance_dashboard import get_overview_stats

    # Use a company that exists
    result = get_overview_stats("Demo Company")

    assert isinstance(result, dict)
    assert "total_companies" in result
    assert "fiscal_devices" in result
    assert "employees" in result
    assert "active_contracts" in result
    assert all(isinstance(v, int) for v in result.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: FAIL with "import error" or "function not defined"

- [ ] **Step 3: Write get_overview_stats implementation**

Add after `get_compliance_status()` in `compliance_dashboard.py`:

```python
def get_overview_stats(company=None):
    """Get overview statistics for dashboard stat cards"""
    if not company:
        company = frappe.defaults.get_user_default("Company")

    if not company:
        return {
            'total_companies': 0,
            'fiscal_devices': 0,
            'employees': 0,
            'active_contracts': 0
        }

    # Count companies in Ethiopia
    total_companies = frappe.db.count("Company", {"country": "Ethiopia"})

    # Count active fiscal devices
    fiscal_devices = frappe.db.count("Fiscal Device", {"status": "Active"})

    # Count employees for this company
    employees = frappe.db.count("Employee", {"company": company, "status": "Active"})

    # Count active contracts
    active_contracts = frappe.db.count("Contract", {"status": "Active", "company": company})

    return {
        'total_companies': total_companies,
        'fiscal_devices': fiscal_devices,
        'employees': employees,
        'active_contracts': active_contracts
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py ethiopia_compliance/accounts/tests/test_dashboard.py
git commit -m "feat(dashboard): add get_overview_stats for stat cards

Adds total_companies, fiscal_devices, employees, active_contracts counts.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 2: Add `get_chart_data()` Function

**Files:**
- Modify: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py` (add after get_overview_stats)

- [ ] **Step 1: Write test for get_chart_data**

```python
def test_get_chart_data():
    """Test that chart data returns expected structure"""
    from ethiopia_compliance.page.compliance_dashboard.compliance_dashboard import get_chart_data

    result = get_chart_data("this_month")

    assert isinstance(result, dict)
    assert "revenue" in result
    assert "expenses" in result
    assert "cash_flow" in result
    assert "taxes" in result
    assert result["taxes"].get("wht") is not None
    assert result["taxes"].get("vat") is not None
    assert result["taxes"].get("tot") is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write get_chart_data implementation**

Add after `get_overview_stats()`:

```python
def get_chart_data(period='this_month', from_date=None, to_date=None):
    """Get chart data for the dashboard - Revenue, Expenses, Cash Flow, Taxes"""
    month_start, month_end, _ = _get_date_range(period, from_date, to_date)
    company = frappe.defaults.get_user_default("Company")

    if not company:
        return {"revenue": [], "expenses": [], "cash_flow": [], "taxes": {"wht": [], "vat": [], "tot": []}}

    # Helper to get monthly data
    def get_monthly_data doctype, date_field, company_filter, amount_field="grand_total"):
        months = {}
        for i in range(12):
            month_start = add_months(today(), -i)
            month_start_dt = datetime.strptime(month_start, '%Y-%m-%d')
            month_end = get_last_day(month_start)
            month_label = month_start_dt.strftime('%b')

            data = frappe.db.sql(f"""
                SELECT SUM({amount_field}) as amount
                FROM `tab{doctype}`
                WHERE {date_field} BETWEEN %s AND %s
                AND company = %s
                AND docstatus = 1
            """, (month_start, month_end.strftime('%Y-%m-%d'), company), as_dict=True)

            months[month_label] = flt(data[0].amount) if data and data[0].amount else 0

        return [{"month": k, "amount": v} for k, v in sorted(months.items())]

    revenue = get_monthly_data("Sales Invoice", "posting_date", company)
    expenses = get_monthly_data("Purchase Invoice", "posting_date", company)

    # Cash flow = revenue - expenses per month
    cash_flow = []
    for rev, exp in zip(revenue, expenses):
        cash_flow.append({"month": rev["month"], "amount": rev["amount"] - exp["amount"]})

    # Tax data using existing get_tax_summary logic but per month
    taxes = {"wht": [], "vat": [], "tot": []}
    for i in range(12):
        month_start = add_months(today(), -i)
        month_start_dt = datetime.strptime(month_start, '%Y-%m-%d')
        month_end = get_last_day(month_start)
        month_label = month_start_dt.strftime('%b')

        # WHT
        wht = frappe.db.sql("""
            SELECT ABS(SUM(ptc.tax_amount)) as amount
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Taxes and Charges` ptc ON ptc.parent = pi.name
            WHERE pi.posting_date BETWEEN %s AND %s
            AND pi.company = %s AND pi.docstatus = 1
            AND (ptc.account_head LIKE '%%Withholding%%' OR ptc.description LIKE '%%WHT%%')
        """, (month_start, month_end.strftime('%Y-%m-%d'), company), as_dict=True)
        taxes["wht"].append({"month": month_label, "amount": flt(wht[0].amount) if wht and wht[0].amount else 0})

        # VAT
        vat = frappe.db.sql("""
            SELECT ABS(SUM(stc.tax_amount)) as amount
            FROM `tabSales Invoice` si
            JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
            WHERE si.posting_date BETWEEN %s AND %s
            AND si.company = %s AND si.docstatus = 1
            AND (stc.account_head LIKE '%%VAT%%' OR stc.description LIKE '%%VAT%%')
        """, (month_start, month_end.strftime('%Y-%m-%d'), company), as_dict=True)
        taxes["vat"].append({"month": month_label, "amount": flt(vat[0].amount) if vat and vat[0].amount else 0})

        # TOT
        try:
            settings = frappe.get_cached_doc("Compliance Setting")
            if settings.get("tot_account"):
                tot = frappe.db.sql("""
                    SELECT ABS(SUM(stc.tax_amount)) as amount
                    FROM `tabSales Invoice` si
                    JOIN `tabSales Taxes and Charges` stc ON stc.parent = si.name
                    WHERE si.posting_date BETWEEN %s AND %s
                    AND si.company = %s AND si.docstatus = 1 AND stc.account_head = %s
                """, (month_start, month_end.strftime('%Y-%m-%d'), company, settings.tot_account), as_dict=True)
                taxes["tot"].append({"month": month_label, "amount": flt(tot[0].amount) if tot and tot[0].amount else 0})
            else:
                taxes["tot"].append({"month": month_label, "amount": 0})
        except Exception:
            taxes["tot"].append({"month": month_label, "amount": 0})

    return {
        "revenue": list(reversed(revenue)),
        "expenses": list(reversed(expenses)),
        "cash_flow": list(reversed(cash_flow)),
        "taxes": {
            "wht": list(reversed(taxes["wht"])),
            "vat": list(reversed(taxes["vat"])),
            "tot": list(reversed(taxes["tot"]))
        }
    }
```

Fix the helper function syntax error on implementation.

- [ ] **Step 4: Run test to verify it passes**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py
git commit -m "feat(dashboard): add get_chart_data for Revenue, Expenses, Cash Flow, Taxes charts

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 3: Modify `get_dashboard_data()` to Include New Data

**Files:**
- Modify: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py:64-89`

- [ ] **Step 1: Update get_dashboard_data return value**

Find the return block in `get_dashboard_data()` and add:

```python
return {
    # existing fields...
    'tax_summary': get_tax_summary(company, month_start, month_end),
    'ethiopian_date': ethiopian_today,
    'gregorian_date': today_date,
    'recent_documents': get_recent_documents(company, month_start, month_end),
    'compliance_status': get_compliance_status(company),
    'tax_calendar': get_tax_calendar(),
    'month_start': month_start,
    'month_end': month_end,
    'period_label': _(period_label),
    'period': period,
    'company': company,
    # NEW:
    'overview_stats': get_overview_stats(company),
    'chart_data': get_chart_data(period, month_start, month_end)
}
```

- [ ] **Step 2: Run test to verify changes**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: PASS (existing tests still work)

- [ ] **Step 3: Commit**

```bash
git add ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.py
git commit -m "feat(dashboard): include overview_stats and chart_data in get_dashboard_data

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 4: Add Stat Cards to compliance_dashboard.js

**Files:**
- Modify: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js`

- [ ] **Step 1: Read existing JS file to understand current structure**

Read: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js`

- [ ] **Step 2: Add stat card HTML template**

Add after the period selector HTML (around line 20-30):

```html
<div class="row stat-cards-row">
    <div class="col-sm-3">
        <div class="stat-card">
            <div class="stat-card-icon bg-primary">
                <i class="fa fa-building"></i>
            </div>
            <div class="stat-card-info">
                <span class="stat-card-label">Total Companies</span>
                <span class="stat-card-value" id="total-companies">--</span>
            </div>
        </div>
    </div>
    <div class="col-sm-3">
        <div class="stat-card">
            <div class="stat-card-icon bg-success">
                <i class="fa fa-hardware"></i>
            </div>
            <div class="stat-card-info">
                <span class="stat-card-label">Fiscal Devices</span>
                <span class="stat-card-value" id="fiscal-devices">--</span>
            </div>
        </div>
    </div>
    <div class="col-sm-3">
        <div class="stat-card">
            <div class="stat-card-icon bg-warning">
                <i class="fa fa-users"></i>
            </div>
            <div class="stat-card-info">
                <span class="stat-card-label">Employees</span>
                <span class="stat-card-value" id="employees">--</span>
            </div>
        </div>
    </div>
    <div class="col-sm-3">
        <div class="stat-card">
            <div class="stat-card-icon bg-info">
                <i class="fa fa-file-contract"></i>
            </div>
            <div class="stat-card-info">
                <span class="stat-card-label">Active Contracts</span>
                <span class="stat-card-value" id="active-contracts">--</span>
            </div>
        </div>
    </div>
</div>
```

- [ ] **Step 3: Add stat card CSS**

Add to the `<style>` section or include via frappe:

```css
.stat-cards-row {
    margin-bottom: 20px;
}
.stat-card {
    background: white;
    border-radius: 8px;
    padding: 20px;
    display: flex;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.stat-card-icon {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 15px;
    color: white;
}
.stat-card-info {
    display: flex;
    flex-direction: column;
}
.stat-card-label {
    font-size: 12px;
    color: #6c757d;
    text-transform: uppercase;
}
.stat-card-value {
    font-size: 24px;
    font-weight: bold;
    color: #2d3748;
}
```

- [ ] **Step 4: Update refresh_dashboard to populate stat cards**

Find the function that processes `get_dashboard_data` response and add:

```javascript
// After getting data...
if (data.overview_stats) {
    $('#total-companies').text(data.overview_stats.total_companies || 0);
    $('#fiscal-devices').text(data.overview_stats.fiscal_devices || 0);
    $('#employees').text(data.overview_stats.employees || 0);
    $('#active-contracts').text(data.overview_stats.active_contracts || 0);
}
```

- [ ] **Step 5: Commit**

```bash
git add ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js
git commit -m "feat(dashboard): add stat cards UI for overview statistics

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 5: Add Charts to compliance_dashboard.js

**Files:**
- Modify: `ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js`

- [ ] **Step 1: Add chart HTML containers**

Add after the stat cards row and before the existing dashboard content:

```html
<div class="row chart-row">
    <div class="col-sm-6">
        <div class="chart-container">
            <h6>Revenue</h6>
            <div id="revenue-chart"></div>
        </div>
    </div>
    <div class="col-sm-6">
        <div class="chart-container">
            <h6>Expenses</h6>
            <div id="expenses-chart"></div>
        </div>
    </div>
</div>
<div class="row chart-row">
    <div class="col-sm-6">
        <div class="chart-container">
            <h6>Cash Flow</h6>
            <div id="cash-flow-chart"></div>
        </div>
    </div>
    <div class="col-sm-6">
        <div class="chart-container">
            <h6>Taxes</h6>
            <div id="taxes-chart"></div>
        </div>
    </div>
</div>
```

- [ ] **Step 2: Add chart CSS**

```css
.chart-row {
    margin-bottom: 20px;
}
.chart-container {
    background: white;
    border-radius: 8px;
    padding: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.chart-container h6 {
    margin-bottom: 15px;
    font-weight: 600;
}
```

- [ ] **Step 3: Add chart rendering functions**

Add using Frappe's chart (based on Chart.js):

```javascript
function render_charts(data) {
    if (!data.chart_data) return;

    const chart_options = {
        autoScale: true,
        showFill: true,
        axisY: {
            showLabel: true,
            onlyInteger: false
        }
    };

    // Revenue Chart
    if (data.chart_data.revenue && data.chart_data.revenue.length > 0) {
        new frappe.chart('#revenue-chart', {
            data: {
                labels: data.chart_data.revenue.map(d => d.month),
                datasets: [{
                    name: 'Revenue',
                    values: data.chart_data.revenue.map(d => d.amount)
                }]
            },
            type: 'line',
            options: chart_options
        });
    }

    // Expenses Chart
    if (data.chart_data.expenses && data.chart_data.expenses.length > 0) {
        new frappe.chart('#expenses-chart', {
            data: {
                labels: data.chart_data.expenses.map(d => d.month),
                datasets: [{
                    name: 'Expenses',
                    values: data.chart_data.expenses.map(d => d.amount)
                }]
            },
            type: 'line',
            options: chart_options
        });
    }

    // Cash Flow Chart
    if (data.chart_data.cash_flow && data.chart_data.cash_flow.length > 0) {
        new frappe.chart('#cash-flow-chart', {
            data: {
                labels: data.chart_data.cash_flow.map(d => d.month),
                datasets: [{
                    name: 'Cash Flow',
                    values: data.chart_data.cash_flow.map(d => d.amount)
                }]
            },
            type: 'bar',
            options: chart_options
        });
    }

    // Taxes Chart (stacked bar for WHT, VAT, TOT)
    if (data.chart_data.taxes) {
        new frappe.chart('#taxes-chart', {
            data: {
                labels: data.chart_data.taxes.wht.map(d => d.month),
                datasets: [
                    { name: 'WHT', values: data.chart_data.taxes.wht.map(d => d.amount) },
                    { name: 'VAT', values: data.chart_data.taxes.vat.map(d => d.amount) },
                    { name: 'TOT', values: data.chart_data.taxes.tot.map(d => d.amount) }
                ]
            },
            type: 'bar',
            options: {
                ...chart_options,
                stacked: true
            }
        });
    }
}
```

- [ ] **Step 4: Call render_charts in refresh_dashboard**

In the `refresh_dashboard` or equivalent function that processes API response, add:

```javascript
// After stat cards population
render_charts(data);
```

- [ ] **Step 5: Test by running bench**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance --module ethiopia_compliance.accounts.tests.test_dashboard 2>&1`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ethiopia_compliance/page/compliance_dashboard/compliance_dashboard.js
git commit -m "feat(dashboard): add Revenue, Expenses, Cash Flow, Taxes charts

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Task 6: Final Integration Test

**Files:**
- No file changes - verification only

- [ ] **Step 1: Run full test suite**

Run: `bench --site [sitename] run-tests --app ethiopia_compliance 2>&1 | head -50`

- [ ] **Step 2: Manual verification**

1. Visit `/app/compliance-dashboard`
2. Verify 4 stat cards appear with correct counts
3. Verify 4 charts render (Revenue, Expenses, Cash Flow, Taxes)
4. Change period selector and verify charts update

- [ ] **Step 3: Commit final changes if any**

```bash
git add -A && git commit -m "chore: complete Ethiopia Compliance dashboard extension

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>" 2>/dev/null || true
```

---

## Spec Coverage Check

- [x] Stat cards (Companies, Fiscal Devices, Employees, Contracts) - Task 1, 4
- [x] Revenue chart - Task 2, 5
- [x] Expenses chart - Task 2, 5
- [x] Cash Flow chart - Task 2, 5
- [x] Taxes chart (WHT, VAT, TOT) - Task 2, 5
- [x] Period selector integration - Task 3 (uses existing _get_date_range)
- [x] Integration with existing dashboard - Task 3

---

## Dependencies

- Frappe Framework (frappe.chart built-in)
- Existing `get_dashboard_data` API (Task 3 modifies it)
- `_get_date_range` helper (already exists)
- `get_tax_summary` (already exists, reused in chart data)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Fiscal Device or Contract doctype doesn't exist | Add defensive checks in `get_overview_stats`, return 0 if doctype missing |
| Chart performance with large datasets | Add 1-hour cache to `get_chart_data` similar to `get_tax_summary` |
| CSS conflicts with existing theme | Use specific class names (`.stat-card`, `.chart-container`) to avoid conflicts |
