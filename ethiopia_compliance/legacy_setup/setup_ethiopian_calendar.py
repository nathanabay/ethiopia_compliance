import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- 🇪🇹 SETTING UP ETHIOPIAN CALENDAR SYSTEM ---")
    
    # 1. Create Custom Fields
    fields = {
        "Sales Invoice": [
            {
                "fieldname": "ethiopian_date",
                "label": "Ethiopian Date (DD-MM-YYYY)",
                "fieldtype": "Data",
                "insert_after": "posting_date",
                "length": 10
            }
        ],
        "Purchase Invoice": [
            {
                "fieldname": "ethiopian_date",
                "label": "Ethiopian Date (DD-MM-YYYY)",
                "fieldtype": "Data",
                "insert_after": "posting_date",
                "length": 10
            }
        ]
    }
    
    create_custom_fields(fields)
    print("✔ Fields Added.")

    # 2. Define Client Script Code
    script_code = """
frappe.ui.form.on(doc.doctype, {
    // 1. If user changes Gregorian Date -> Update Ethiopian
    posting_date: function(frm) {
        if (frm.doc.posting_date) {
            frappe.call({
                method: "ethiopia_compliance.utils.get_ec_date",
                args: { date: frm.doc.posting_date },
                callback: function(r) {
                    if (r.message && r.message !== frm.doc.ethiopian_date) {
                        frm.set_value('ethiopian_date', r.message);
                    }
                }
            });
        }
    },

    // 2. If user types Ethiopian Date -> Update Gregorian
    ethiopian_date: function(frm) {
        if (frm.doc.ethiopian_date && frm.doc.ethiopian_date.length >= 8) {
            frappe.call({
                method: "ethiopia_compliance.utils.get_gc_date",
                args: { ethiopian_date: frm.doc.ethiopian_date },
                callback: function(r) {
                    if (r.message) {
                        frm.set_value('posting_date', r.message);
                        frappe.show_alert({message: "Synced with Gregorian Calendar", indicator: "green"});
                    } else {
                        frappe.msgprint("Invalid Ethiopian Date. Use DD-MM-YYYY format.");
                    }
                }
            });
        }
    }
});
    """

    # 3. Create/Update Client Scripts
    doctypes = ["Sales Invoice", "Purchase Invoice"]
    
    for dt in doctypes:
        script_name = f"Ethiopian Calendar Sync - {dt}"
        
        # Delete if exists to update
        if frappe.db.exists("Client Script", script_name):
            frappe.delete_doc("Client Script", script_name)
            
        doc = frappe.get_doc({
            "doctype": "Client Script",
            "dt": dt,
            "name": script_name,
            "script": script_code,
            "enabled": 1,
            "view": "Form"
        })
        doc.insert(ignore_permissions=True)
        print(f"✔ Script Installed for: {dt}")

    frappe.db.commit()
    print("--- ✅ SYSTEM READY ---")
