app_name = "ethiopia_compliance"
app_title = "Ethiopia Compliance"
app_publisher = "Bespo"
app_description = "TASS Reports, Ethiopian Calendar, and WHT Compliance for ERPNext"
app_email = "admin@bespo.et"
app_license = "MIT"

# --- 1. CAPTURE THESE CHANGES (FIXTURES) ---
# This tells ERPNext to save these DB changes into files
fixtures = [
    {"dt": "Custom Field", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Client Script", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Server Script", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Property Setter", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Workflow", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Workflow State", "filters": [["module", "=", "Ethiopia Compliance"]]},
    {"dt": "Workspace", "filters": [["module", "=", "Ethiopia Compliance"]]},
    # Capture the specific 2017 EC Calendar we made
    {"dt": "Fiscal Year", "filters": [["name", "=", "2017 E.C."]]}
]

# --- 2. AUTOMATICALLY APPLY WHT LOGIC ---
# This connects the Python WHT logic to Purchase Invoices
doc_events = {
    "Purchase Invoice": {
        "before_save": "ethiopia_compliance.accounts.wht_logic.apply_withholding_tax"
    }
}

# --- 3. GLOBAL ASSETS ---
app_include_js = [
    "/assets/ethiopia_compliance/js/ethiopian_calendar.js",
    "/assets/ethiopia_compliance/js/tin_validation.js"
]

# --- 4. REQUIRED APPS ---
required_apps = ["erpnext"]
