import frappe

def run():
    print("--- Fixing Report Visibility & Permissions ---")
    
    # List of reports and the roles that should see them
    reports = [
        ("TASS Purchase Declaration", ["Accounts Manager", "Auditor", "System Manager"]),
        ("TASS Sales Declaration", ["Accounts Manager", "Auditor", "System Manager"]),
        ("SIGTAS Withholding Report", ["Accounts Manager", "Auditor", "System Manager"]),
        ("Ethiopia Schedule A", ["HR Manager", "Accounts Manager", "System Manager"])
    ]

    for report_name, roles in reports:
        if not frappe.db.exists("Report", report_name):
            print(f"⚠ Report '{report_name}' is MISSING. Please re-run the installation scripts.")
            continue
        
        doc = frappe.get_doc("Report", report_name)
        
        # 1. Ensure it is not disabled
        doc.disabled = 0
        
        # 2. Add Roles
        current_roles = [r.role for r in doc.roles]
        dirty = False
        
        for role in roles:
            if role not in current_roles:
                doc.append("roles", {"role": role})
                dirty = True
                print(f"   + Added Role: {role} to {report_name}")
        
        if dirty:
            doc.save(ignore_permissions=True)
            print(f"✔ Permissions Updated: {report_name}")
        else:
            print(f"✔ {report_name} is already configured.")

    frappe.db.commit()
    print("--- Done. Clearing Cache... ---")
    frappe.clear_cache()
