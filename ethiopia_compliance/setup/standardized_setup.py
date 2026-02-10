
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🇪🇹 STARTING ETHIOPIA COMPLIANCE STANDARDIZED SETUP ---")
    
    # 1. CONSOLIDATED CUSTOM FIELDS
    setup_custom_fields()
    
    # 2. INCOME TAX SLABS (2025/2026)
    create_income_tax_slabs()
    
    # 3. ACCOUNTS & TAX TEMPLATES
    setup_accounts_and_templates()
    
    # 4. FISCAL YEAR (2017 E.C.)
    setup_fiscal_year()

    # 5. COMPLIANCE SETTINGS
    setup_compliance_settings()
    
    frappe.db.commit()
    print("--- ✅ SUCCESS: ETHIOPIA COMPLIANCE STANDARDIZED ---")

def setup_custom_fields():
    print("👉 Standardizing Custom Fields...")
    
    # Target DocTypes for the Ethiopian Calendar
    calendar_doctypes = [
        "Sales Invoice", "Purchase Invoice", "Journal Entry", "Payment Entry", 
        "Purchase Order", "Sales Order", "Leave Application", "Attendance", 
        "Salary Slip", "Employee", "Expense Claim", "Job Offer", "Stock Entry", 
        "Delivery Note", "Purchase Receipt", "Material Request", 
        "Stock Reconciliation", "Project", "Asset"
    ]

    custom_fields = {}

    # A. Ethiopian Date Field (System-wide)
    for dt in calendar_doctypes:
        insert_after = "posting_date"
        if dt in ["Employee", "Job Offer"]: insert_after = "date_of_joining"
        elif dt == "Leave Application": insert_after = "from_date"
        elif dt == "Attendance": insert_after = "attendance_date"
        elif dt == "Project": insert_after = "expected_start_date"
        elif dt == "Asset": insert_after = "purchase_date"
        elif dt in ["Salary Slip", "Material Request"]: insert_after = "transaction_date"

        if dt not in custom_fields: custom_fields[dt] = []
        custom_fields[dt].append({
            "fieldname": "ethiopian_date",
            "label": "📅 Ethiopian Date",
            "fieldtype": "Data",
            "insert_after": insert_after,
            "length": 10,
            "description": "Format: DD-MM-YYYY",
            "module": "Ethiopia Compliance"
        })

    # B. Company Compliance Fields (VAT + Commercial Code)
    comp_fields = [
        {"fieldname": "custom_vat_reg_number", "label": "VAT Registration Number", "fieldtype": "Data", "insert_after": "tax_id", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_trade_name", "label": "Trade Name", "fieldtype": "Data", "insert_after": "company_name", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_auditor_name", "label": "External Auditor", "fieldtype": "Data", "insert_after": "tax_id", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_auditor_term_end", "label": "Auditor Term End", "fieldtype": "Date", "insert_after": "custom_auditor_name", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_nominee_name", "label": "Nominee (For OPPLC)", "fieldtype": "Data", "insert_after": "custom_auditor_term_end", "module": "Ethiopia Compliance"}
    ]
    if "Company" not in custom_fields: custom_fields["Company"] = []
    custom_fields["Company"].extend(comp_fields)

    # C. Employee HR Fields
    emp_fields = [
        {"fieldname": "custom_pension_number", "label": "Pension Number", "fieldtype": "Data", "insert_after": "tax_id", "unique": 0, "module": "Ethiopia Compliance"},
        {"fieldname": "custom_mothers_name", "label": "Mother's Name", "fieldtype": "Data", "insert_after": "last_name", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_kebele", "label": "Kebele", "fieldtype": "Data", "insert_after": "current_address", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_house_number", "label": "House Number", "fieldtype": "Data", "insert_after": "custom_kebele", "module": "Ethiopia Compliance"}
    ]
    if "Employee" not in custom_fields: custom_fields["Employee"] = []
    custom_fields["Employee"].extend(emp_fields)

    # D. Supplier & Multi-Doc Compliance
    if "Supplier" not in custom_fields: custom_fields["Supplier"] = []
    custom_fields["Supplier"].extend([
        {"fieldname": "custom_wht_eligible", "label": "WHT Eligible (2%)", "fieldtype": "Check", "insert_after": "tax_id", "default": "0", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_vat_registered", "label": "VAT Registered", "fieldtype": "Check", "insert_after": "custom_wht_eligible", "default": "1", "module": "Ethiopia Compliance"}
    ])

    if "Sales Invoice" not in custom_fields: custom_fields["Sales Invoice"] = []
    custom_fields["Sales Invoice"].extend([
        {"fieldname": "custom_fs_number", "label": "FS Number", "fieldtype": "Data", "insert_after": "taxes_and_charges", "description": "Fiscal Signature", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_fiscal_machine_no", "label": "Fiscal Machine No", "fieldtype": "Data", "insert_after": "custom_fs_number", "module": "Ethiopia Compliance"}
    ])

    if "Purchase Invoice" not in custom_fields: custom_fields["Purchase Invoice"] = []
    custom_fields["Purchase Invoice"].extend([
        {"fieldname": "custom_supplier_tin", "label": "Supplier TIN", "fieldtype": "Data", "insert_after": "supplier_address", "fetch_from": "supplier.tax_id", "module": "Ethiopia Compliance"},
        {"fieldname": "custom_wht_receipt_no", "label": "WHT Receipt Number", "fieldtype": "Data", "insert_after": "taxes_and_charges", "module": "Ethiopia Compliance"}
    ])

    if "Item" not in custom_fields: custom_fields["Item"] = []
    custom_fields["Item"].append({"fieldname": "custom_hs_code", "label": "HS Code", "fieldtype": "Data", "insert_after": "item_group", "module": "Ethiopia Compliance"})

    create_custom_fields(custom_fields, update=True)

def create_income_tax_slabs():
    print("👉 Setup Income Tax Slabs...")
    slab_name = "Ethiopia Tax 2025/2026"
    if not frappe.db.exists("Income Tax Slab", slab_name):
        doc = frappe.get_doc({
            "doctype": "Income Tax Slab",
            "name": slab_name,
            "currency": "ETB",
            "effective_from": "2025-07-08",
            "allow_tax_exemption": 1,
            "slabs": [
                {"from_amount": 0, "to_amount": 2000, "percent_deduction": 0},
                {"from_amount": 2001, "to_amount": 4000, "percent_deduction": 15},
                {"from_amount": 4001, "to_amount": 7000, "percent_deduction": 20},
                {"from_amount": 7001, "to_amount": 10000, "percent_deduction": 25},
                {"from_amount": 10001, "to_amount": 14000, "percent_deduction": 30},
                {"from_amount": 14001, "to_amount": 9999999, "percent_deduction": 35}
            ]
        })
        doc.insert(ignore_permissions=True)

def setup_accounts_and_templates():
    print("👉 Setting up Accounts & Tax Templates...")
    company = frappe.defaults.get_user_default("Company")
    if not company: return

    accounts = [
        ("Input VAT 15%", "Duties and Taxes", "Tax", "Asset"),
        ("TOT Expense", "Direct Expenses", "Chargeable", "Expense"),
        ("Withholding Tax", "Duties and Taxes", "Tax", "Asset"),
        ("Customs Duty", "Direct Expenses", "Chargeable", "Expense"),
        ("Sur Tax", "Direct Expenses", "Chargeable", "Expense"),
        ("Excise Tax", "Direct Expenses", "Chargeable", "Expense")
    ]
    
    account_map = {}
    for name, parent_partial, acc_type, root_type in accounts:
        existing = frappe.db.get_value("Account", {"account_name": ["like", f"{name}%"], "company": company})
        if existing:
            account_map[name] = existing
        else:
            parent = frappe.db.get_value("Account", {"account_name": ["like", f"%{parent_partial}%"], "company": company, "is_group": 1})
            if parent:
                new_acc = frappe.get_doc({
                    "doctype": "Account", "account_name": name, "company": company, 
                    "parent_account": parent, "account_type": acc_type, "currency": "ETB",
                    "report_type": "Balance Sheet" if root_type == "Asset" else "Profit and Loss"
                })
                new_acc.insert(ignore_permissions=True)
                account_map[name] = new_acc.name

    # Create Templates
    def template_exists(title, company):
        return frappe.db.exists("Purchase Taxes and Charges Template", {"title": title, "company": company}) or \
               frappe.db.exists("Purchase Taxes and Charges Template", {"title": ["like", f"{title}%"], "company": company})

    if "Input VAT 15%" in account_map and not template_exists("Ethiopia Local VAT 15%", company):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template", "title": "Ethiopia Local VAT 15%", "company": company,
            "taxes": [{"charge_type": "On Net Total", "account_head": account_map["Input VAT 15%"], "description": "VAT 15%", "rate": 15}]
        }).insert(ignore_permissions=True)

    if "TOT Expense" in account_map and not template_exists("Ethiopia Local TOT 2%", company):
        frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template", "title": "Ethiopia Local TOT 2%", "company": company,
            "taxes": [{"charge_type": "On Net Total", "account_head": account_map["TOT Expense"], "description": "TOT 2%", "rate": 2}]
        }).insert(ignore_permissions=True)

def setup_fiscal_year():
    print("👉 Setup Fiscal Year 2017 E.C...")
    fy_name = "2017 E.C."
    if not frappe.db.exists("Fiscal Year", fy_name):
        doc = frappe.get_doc({
            "doctype": "Fiscal Year", "year": fy_name, 
            "year_start_date": "2024-09-11", "year_end_date": "2025-09-10"
        })
        company = frappe.defaults.get_user_default("Company")
        if company: doc.append("companies", {"company": company})
        doc.insert(ignore_permissions=True)

def setup_compliance_settings():
    print("👉 Setting up Compliance Settings...")
    try:
        settings = frappe.get_single("Compliance Setting")
        # Only set if not already set (to avoid overwriting user changes)
        if not settings.wht_goods_threshold:
            settings.wht_goods_threshold = 10000
            settings.wht_services_threshold = 3000
            settings.wht_rate = 2
            settings.vat_rate = 15
            settings.save(ignore_permissions=True)
    except Exception as e:
        print(f"⚠️ Could not setup Compliance Settings: {e}")
