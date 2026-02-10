import frappe

def run():
    print("--- Fixing Report Configurations ---")
    
    reports = [
        "TASS Purchase Declaration", 
        "TASS Sales Declaration", 
        "SIGTAS Withholding Report", 
        "Ethiopia Schedule A"
    ]
    
    for report_name in reports:
        if frappe.db.exists("Report", report_name):
            # 1. Force 'is_standard' to Yes (1)
            # This tells ERPNext: "The code for this report is in a file, go find it."
            frappe.db.set_value("Report", report_name, "is_standard", 1)
            
            # 2. Ensure Report Type is 'Script Report'
            frappe.db.set_value("Report", report_name, "report_type", "Script Report")
            
            print(f"✔ Fixed: {report_name} (Now linked to file system)")
        else:
            print(f"⚠ Report not found: {report_name}")

    frappe.db.commit()
    print("--- Clearing Cache to apply changes ---")
    frappe.clear_cache()
