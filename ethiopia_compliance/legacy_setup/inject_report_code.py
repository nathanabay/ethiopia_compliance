import frappe
import os

def run():
    print("--- 💉 INJECTING PYTHON CODE INTO DATABASE ---")
    
    # Map Report Name to Folder Name
    reports = {
        "TASS Purchase Declaration": "tass_purchase_declaration",
        "TASS Sales Declaration": "tass_sales_declaration",
        "SIGTAS Withholding Report": "sigtas_withholding_report",
        "Ethiopia Schedule A": "ethiopia_schedule_a"
    }
    
    base_path = frappe.get_app_path("ethiopia_compliance", "report")
    
    for report_name, folder_name in reports.items():
        # 1. Read the Python File
        file_path = os.path.join(base_path, folder_name, f"{folder_name}.py")
        
        if not os.path.exists(file_path):
            print(f"❌ File Missing: {file_path}")
            continue
            
        with open(file_path, "r") as f:
            code_content = f.read()
            
        # 2. Update Database
        if frappe.db.exists("Report", report_name):
            # Force it to be a Custom Report (is_standard=0) with the Code injected
            frappe.db.sql("""
                UPDATE `tabReport` 
                SET 
                    is_standard = 0, 
                    report_type = 'Script Report', 
                    report_script = %s,
                    disabled = 0
                WHERE name = %s
            """, (code_content, report_name))
            
            print(f"✔ Code Injected for: {report_name}")
        else:
            print(f"⚠ Report Doc not found: {report_name}")

    frappe.db.commit()
    print("--- 💾 Clearing Cache ---")
    frappe.clear_cache()
    print("--- ✅ DONE ---")
