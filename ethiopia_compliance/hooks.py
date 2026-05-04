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
			# Phase 1.3: Updated WHT Rules Engine (Article 97)
			"ethiopia_compliance.accounts.wht_logic.apply_withholding_tax"
		],
		"on_submit": [
			# Phase 1.6: Automated WHT Certificates — triggered at invoice submission
			"ethiopia_compliance.accounts.wht_certificate_logic.on_invoice_submit"
		]
	},
	"Sales Invoice": {
		"before_submit": [
			"ethiopia_compliance.integrations.fiscal_device.register_sales_invoice",
			"ethiopia_compliance.accounts.invoice_logic.validate_fs_number"
		]
	},
	"Payment Entry": {
		"validate": [
			# Phase 1.2: Strict Cash Transaction Blocker (Article 81 / 1395/2017)
			"ethiopia_compliance.accounts.payment_logic.validate_cash_limits"
		],
		"on_submit": [
			# Phase 1.6: Automated WHT Certificates — triggered at payment
			"ethiopia_compliance.accounts.wht_certificate_logic.on_payment_submit"
		]
	},
	"Journal Entry": {
		"validate": [
			# Phase 1.2: Cash Transaction Blocker — applies to cash account debits/credits
			"ethiopia_compliance.accounts.payment_logic.validate_cash_limits"
		],
		"on_submit": [
			"ethiopia_compliance.accounts.payment_logic.validate_journal_entry_on_submit"
		]
	},
	"Purchase Order": {
		"validate": [
			# Phase 1.7: Server-side TIN warning / audit trail
			"ethiopia_compliance.accounts.po_logic.warn_missing_supplier_tin"
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
		# Phase 1.7: Check for overdue pension remittances (>30 days)
		"ethiopia_compliance.tasks.compliance_alerts.check_overdue_pension",
	],
	"weekly": [
		# Phase 1.7: Weekly tax deadline digest (within 7 days of deadline)
		"ethiopia_compliance.tasks.compliance_alerts.send_tax_deadline_digest",
	],
	"monthly": [
		# Phase 1.7: Monthly 25th — CFO VAT/WHT/Pension deadline reminder
		"ethiopia_compliance.tasks.compliance_alerts.send_monthly_deadline_reminder",
		# Phase 1.7: End-of-month unremitted pension alert to HR
		"ethiopia_compliance.tasks.compliance_alerts.check_unremitted_pension_end_of_month",
	]
}

# --- 4. GLOBAL ASSETS ---
app_include_js = [
	"/assets/ethiopia_compliance/js/ethiopian_calendar.js",
	"/assets/ethiopia_compliance/js/tin_validation.js",
	# Phase 1.7: Purchase Order TIN warning (client-side msgprint)
	"/assets/ethiopia_compliance/js/wht_po_warning.js"
]

# --- 5. REQUIRED APPS ---
required_apps = ["erpnext"]