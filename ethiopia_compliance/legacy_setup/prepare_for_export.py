import frappe

def run():
    print("--- 📦 PACKAGING MODULE FOR EXPORT ---")
    
    module = "Ethiopia Compliance"
    
    # 1. Assign Client Scripts (Calendar Logic)
    frappe.db.sql("UPDATE `tabClient Script` SET module=%s WHERE name LIKE 'EC Sync%'", (module,))
    frappe.db.sql("UPDATE `tabClient Script` SET module=%s WHERE name LIKE 'Ethiopian%'", (module,))
    print("✔ Linked Client Scripts")

    # 2. Assign Reports (TASS, SIGTAS)
    reports = ["TASS Sales Declaration", "TASS Purchase Declaration", "SIGTAS Withholding Report", "TASS Purchase Excel Export"]
    for r in reports:
        if frappe.db.exists("Report", r):
            frappe.db.set_value("Report", r, "module", module)
            # Ensure they are 'Standard=No' so they export as data fixtures (easiest portability)
            frappe.db.set_value("Report", r, "is_standard", "No")
    print("✔ Linked Reports")

    # 3. Assign Custom Fields (Ethiopian Date)
    frappe.db.sql("UPDATE `tabCustom Field` SET module=%s WHERE fieldname='ethiopian_date'", (module,))
    print("✔ Linked Custom Fields")

    frappe.db.commit()
    print("--- ✅ READY TO EXPORT ---")
