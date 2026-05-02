app_name = "ethiopia_compliance"
app_title = "Ethiopia Compliance"
app_publisher = "Bespo"
app_description = "TASS Reports, Ethiopian Calendar, and WHT Compliance for ERPNext"
app_email = "admin@bespo.et"
app_license = "MIT"

# --- 1. CAPTURE THESE CHANGES (FIXTURES) ---
fixtures = [
	{"dt": "Custom Field", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Client Script", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Server Script", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Workflow", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Workflow State", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Workspace", "filters": [["module", "=", "Ethiopia Compliance"]]},
	{"dt": "Fiscal Year", "filters": [["name", "=", "2017 E.C."]]}
]

# --- 2. DOC EVENTS ---
doc_events = {
	"Purchase Invoice": {
		"before_save": [
			"ethiopia_compliance.accounts.wht_logic.apply_withholding_tax"
		]
	},
	"Sales Invoice": {
		"before_submit": [
			"ethiopia_compliance.accounts.invoice_logic.validate_fs_number"
		]
	},
	"Payment Entry": {
		"validate": [
			"ethiopia_compliance.accounts.payment_logic.validate_cash_limits"
		]
	},
	"Supplier": {
		"validate": [
			"ethiopia_compliance.utils.tin_validator.validate_party_tin"
		]
	},
	"Customer": {
		"validate": [
			"ethiopia_compliance.utils.tin_validator.validate_party_tin"
		]
	},
	"Employee": {
		"validate": [
			"ethiopia_compliance.hr.employee_logic.validate_employee"
		]
	}
}

# --- 3. SCHEDULED EVENTS ---
scheduler_events = {
	"daily": [
		"ethiopia_compliance.overrides.leave_allocation.run_daily_leave_update",
	]
}

# --- 4. GLOBAL ASSETS ---
app_include_js = [
	"/assets/ethiopia_compliance/js/ethiopian_calendar.js",
	"/assets/ethiopia_compliance/js/tin_validation.js"
]

# --- 5. REQUIRED APPS ---
required_apps = ["erpnext"]
