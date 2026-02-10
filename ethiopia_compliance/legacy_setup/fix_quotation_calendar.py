import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🔧 ADDING ETHIOPIAN CALENDAR TO QUOTATION ---")
    
    doctype = "Quotation"
    
    # 1. IDENTIFY THE CORRECT DATE FIELD
    # Quotations usually use 'transaction_date', but sometimes just 'date'
    meta = frappe.get_meta(doctype)
    target_field = "transaction_date"
    
    if not meta.has_field(target_field):
        target_field = "date"
        
    print(f"✔ Target Date Field: {target_field}")

    # 2. CREATE CUSTOM FIELD
    if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": "ethiopian_date"}):
        create_custom_fields({
            doctype: [{
                "fieldname": "ethiopian_date",
                "label": "📅 Ethiopian Date",
                "fieldtype": "Data",
                "read_only": 0,
                "insert_after": target_field,
                "length": 10,
                "description": "Format: DD-MM-YYYY"
            }]
        })
        print("✔ 'Ethiopian Date' field added to Quotation.")
    else:
        print("ℹ 'Ethiopian Date' field already exists (updating logic...)")

    # 3. INJECT CLIENT SCRIPT (SYNC LOGIC)
    script_name = f"EC Sync - {doctype}"
    
    script_code = f"""
frappe.ui.form.on('{doctype}', {{
    refresh: function(frm) {{
        // Auto-fill on load
        if (frm.doc.{target_field} && !frm.doc.ethiopian_date) {{
            frm.trigger('{target_field}');
        }}
    }},
    // 1. Gregorian -> Ethiopian
    {target_field}: function(frm) {{
        if (frm.doc.{target_field}) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_ec_date",
                args: {{ date: frm.doc.{target_field} }},
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
                        frm.set_value('{target_field}', r.message);
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

    # Delete old script if exists to ensure clean update
    if frappe.db.exists("Client Script", script_name):
        frappe.delete_doc("Client Script", script_name)

    # Create new script
    doc = frappe.get_doc({
        "doctype": "Client Script",
        "dt": doctype,
        "name": script_name,
        "script": script_code,
        "enabled": 1,
        "view": "Form"
    })
    doc.insert(ignore_permissions=True)
    
    frappe.db.commit()
    frappe.clear_cache()
    print(f"✔ Logic Installed. Please reload your browser.")
    print("--- ✅ DONE ---")
