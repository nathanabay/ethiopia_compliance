import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🇪🇹 UNIVERSAL ETHIOPIAN CALENDAR ROLLOUT ---")

    # 1. DEFINE TARGET MODULES (Where we want the calendar)
    target_modules = [
        "Accounts", "Stock", "Buying", "Selling", "HR", "Payroll", 
        "Projects", "Assets", "Support", "CRM", "Quality Management"
    ]

    # 2. FIND ALL RELEVANT DOCTYPES DYNAMICALLY
    # We look for forms that are NOT tables, NOT reports, and belong to the modules above.
    doctypes = frappe.get_all("DocType", filters={
        "module": ["in", target_modules],
        "istable": 0,
        "issingle": 0,
        "custom": 0
    }, pluck="name")

    print(f"🔎 Scanning {len(doctypes)} Documents...")
    
    updated_count = 0

    for dt in doctypes:
        # Skip internal system docs to be safe
        if dt.startswith("Role") or dt.startswith("User") or dt.startswith("Print"):
            continue

        # 3. DETECT STANDARD DATE FIELD
        # We need to know where to insert the Ethiopian Date (next to the real date)
        meta = frappe.get_meta(dt)
        target_field = None
        
        # Priority list of date fields to look for
        for candidate in ["posting_date", "transaction_date", "date_of_joining", "attendance_date", "valid_from", "date"]:
            if meta.has_field(candidate):
                target_field = candidate
                break
        
        if target_field:
            # 4. INJECT CUSTOM FIELD
            if not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "ethiopian_date"}):
                create_custom_fields({
                    dt: [{
                        "fieldname": "ethiopian_date",
                        "label": "📅 Ethiopian Date",
                        "fieldtype": "Data",
                        "read_only": 0, # Editable for Bi-Directional Sync
                        "insert_after": target_field,
                        "length": 10,
                        "description": "Format: DD-MM-YYYY"
                    }]
                })
                
                # 5. INJECT CLIENT SCRIPT (THE SYNC LOGIC)
                create_sync_script(dt, target_field)
                print(f"✔ Enabled Ethiopian Calendar on: {dt}")
                updated_count += 1

    print(f"✨ Successfully updated {updated_count} Forms with Dual-Calendar System.")

    # 6. FIX FISCAL YEAR (Solves the Overlap Error)
    create_fiscal_year()
    
    frappe.db.commit()
    frappe.clear_cache()
    print("--- ✅ DONE ---")

def create_sync_script(doctype, date_field):
    """Creates a script that syncs Gregorian <-> Ethiopian instantly"""
    script_name = f"EC Sync - {doctype}"
    
    # JavaScript Logic
    script_code = f"""
frappe.ui.form.on('{doctype}', {{
    refresh: function(frm) {{
        if (frm.doc.{date_field} && !frm.doc.ethiopian_date) {{
            frm.trigger('{date_field}');
        }}
    }},
    // 1. Gregorian -> Ethiopian
    {date_field}: function(frm) {{
        if (frm.doc.{date_field}) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_ec_date",
                args: {{ date: frm.doc.{date_field} }},
                callback: function(r) {{
                    if (r.message && r.message !== frm.doc.ethiopian_date) {{
                        frm.set_value('ethiopian_date', r.message);
                    }}
                }}
            }});
        }}
    }},
    // 2. Ethiopian -> Gregorian
    ethiopian_date: function(frm) {{
        if (frm.doc.ethiopian_date && frm.doc.ethiopian_date.length >= 8) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_gc_date",
                args: {{ ethiopian_date: frm.doc.ethiopian_date }},
                callback: function(r) {{
                    if (r.message) {{
                        frm.set_value('{date_field}', r.message);
                        frappe.show_alert({{message: "📅 Synced to Gregorian", indicator: "green"}});
                    }} else {{
                        frappe.msgprint("Invalid Ethiopian Date. Use DD-MM-YYYY");
                    }}
                }}
            }});
        }}
    }}
}});
    """
    
    if frappe.db.exists("Client Script", script_name):
        frappe.delete_doc("Client Script", script_name)

    doc = frappe.get_doc({
        "doctype": "Client Script",
        "dt": doctype,
        "name": script_name,
        "script": script_code,
        "enabled": 1,
        "view": "Form"
    })
    doc.insert(ignore_permissions=True)

def create_fiscal_year():
    """Creates the 2017 E.C. Fiscal Year linked to BESPO to avoid conflicts"""
    print("--- 🗓 CONFIGURING FISCAL YEAR ---")
    fiscal_year_name = "2017 E.C."
    company_name = "BESPO" 
    
    # Ensure Company Exists
    if not frappe.db.exists("Company", company_name):
        company_name = frappe.defaults.get_user_default("Company")

    if not frappe.db.exists("Fiscal Year", fiscal_year_name):
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": fiscal_year_name,
            "year_start_date": "2024-09-11",
            "year_end_date": "2025-09-10",
            "disabled": 0
        })
        # Link specifically to Company to allow overlap with Gregorian
        fy.append("companies", {"company": company_name})
        fy.insert(ignore_permissions=True)
        print(f"✔ Created Fiscal Year: {fiscal_year_name} for {company_name}")
    else:
        print(f"✔ Fiscal Year {fiscal_year_name} already exists.")

