import frappe
import os

def run():
    print("--- 💉 INJECTING SANITIZED CODE (NO IMPORTS) ---")
    
    reports = {
        "TASS Purchase Declaration": "tass_purchase_declaration",
        "TASS Sales Declaration": "tass_sales_declaration",
        "SIGTAS Withholding Report": "sigtas_withholding_report",
        "Ethiopia Schedule A": "ethiopia_schedule_a"
    }
    
    base_path = frappe.get_app_path("ethiopia_compliance", "report")
    
    for report_name, folder_name in reports.items():
        file_path = os.path.join(base_path, folder_name, f"{folder_name}.py")
        
        if not os.path.exists(file_path):
            print(f"❌ File Missing: {file_path}")
            continue
            
        with open(file_path, "r") as f:
            lines = f.readlines()

        # SANITIZATION: Remove forbidden import lines
        clean_lines = []
        for line in lines:
            if line.strip().startswith("import frappe") or line.strip().startswith("import os"):
                continue # Skip imports
            clean_lines.append(line)
        
        code_content = "".join(clean_lines)
            
        # Update Database with cleaned code
        if frappe.db.exists("Report", report_name):
            frappe.db.sql("""
                UPDATE `tabReport` 
                SET 
                    is_standard = 0, 
                    report_type = 'Script Report', 
                    report_script = %s,
                    disabled = 0
                WHERE name = %s
            """, (code_content, report_name))
            
            print(f"✔ Code Cleaned & Injected for: {report_name}")
        else:
            print(f"⚠ Report Doc not found: {report_name}")

    frappe.db.commit()
    print("--- 💾 Cache Cleared ---")
    frappe.clear_cache()
