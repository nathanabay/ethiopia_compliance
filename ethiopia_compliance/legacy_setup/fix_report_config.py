import frappe
import json
from frappe.utils import today, add_months

def run():
    print("--- 🔧 FIXING REPORT FILTERS & DEBUGGING ---")
    
    # 1. Define Standard Filters (Company, Date Range)
    standard_filters = [
        {
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": "From Date",
            "fieldtype": "Date",
            "default": "2026-01-01",
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": "To Date",
            "fieldtype": "Date",
            "default": today(),
            "reqd": 1
        }
    ]
    
    reports = ["TASS Sales Declaration", "TASS Purchase Declaration", "SIGTAS Withholding Report", "Ethiopia Schedule A"]

    for report in reports:
        if frappe.db.exists("Report", report):
            doc = frappe.get_doc("Report", report)
            
            # A. Inject Filter JSON
            doc.json = json.dumps(standard_filters)
            
            # B. Inject Debugging Python Code
            # This adds a msgprint to show you exactly what is happening
            original_code = doc.report_script
            
            # Only add debug if not already there
            if "frappe.msgprint" not in original_code:
                debug_line = '\n    frappe.msgprint(f"🔎 DEBUG: Query returned {len(data)} rows for range {filters.get(\'from_date\')} to {filters.get(\'to_date\')}")\n'
                # Insert debug line before return
                new_code = original_code.replace("return columns, data", debug_line + "    return columns, data")
                doc.report_script = new_code
            
            doc.save(ignore_permissions=True)
            print(f"✔ Fixed Config & Added Debugger: {report}")
        else:
            print(f"⚠ Report Not Found: {report}")

    frappe.db.commit()
    print("--- 💾 Cache Cleared ---")
    frappe.clear_cache()
