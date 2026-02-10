import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import getdate, add_days

def run():
    print("--- 🇪🇹 GLOBALIZING ETHIOPIAN CALENDAR (HR, ERPNEXT, FRAPPE) ---")

    # ====================================================
    # 1. LIST OF DOCTYPES TO "ETHIOPIANIZE"
    # ====================================================
    target_doctypes = [
        # Accounting
        "Sales Invoice", "Purchase Invoice", "Journal Entry", "Payment Entry", "Purchase Order", "Sales Order",
        # HRMS (HR)
        "Leave Application", "Attendance", "Salary Slip", "Employee", "Expense Claim", "Job Offer",
        # Stock
        "Stock Entry", "Delivery Note", "Purchase Receipt", "Material Request", "Stock Reconciliation",
        # Projects & Assets
        "Project", "Asset"
    ]

    print(f"👉 Target Documents: {len(target_doctypes)} System-wide Forms")

    # ====================================================
    # 2. INJECT CUSTOM FIELDS (The "Ethiopian Date" Field)
    # ====================================================
    for dt in target_doctypes:
        insert_after = "posting_date"
        if dt in ["Employee", "Job Offer"]: insert_after = "date_of_joining"
        elif dt in ["Leave Application"]: insert_after = "from_date"
        elif dt in ["Attendance"]: insert_after = "attendance_date"
        elif dt in ["Project"]: insert_after = "expected_start_date"
        
        if not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "ethiopian_date"}):
            create_custom_fields({
                dt: [{
                    "fieldname": "ethiopian_date",
                    "label": "📅 Ethiopian Date",
                    "fieldtype": "Data",
                    "read_only": 0,
                    "insert_after": insert_after,
                    "length": 10,
                    "description": "Format: DD-MM-YYYY (e.g., 01-01-2017)"
                }]
            })
            print(f"✔ Field added to: {dt}")

    # ====================================================
    # 3. INJECT SYNC LOGIC
    # ====================================================
    script_code = """
frappe.ui.form.on(doc.doctype, {
    refresh: function(frm) {
        if (frm.doc.posting_date && !frm.doc.ethiopian_date) {
            frm.trigger('posting_date');
        }
    },
    posting_date: function(frm) { update_ethiopian(frm, 'posting_date'); },
    transaction_date: function(frm) { update_ethiopian(frm, 'transaction_date'); },
    attendance_date: function(frm) { update_ethiopian(frm, 'attendance_date'); },
    from_date: function(frm) { update_ethiopian(frm, 'from_date'); },
    
    ethiopian_date: function(frm) {
        if (frm.doc.ethiopian_date && frm.doc.ethiopian_date.length >= 8) {
            frappe.call({
                method: "ethiopia_compliance.utils.get_gc_date",
                args: { ethiopian_date: frm.doc.ethiopian_date },
                callback: function(r) {
                    if (r.message) {
                        let target = 'posting_date';
                        if(frm.fields_dict['transaction_date']) target = 'transaction_date';
                        if(frm.fields_dict['attendance_date']) target = 'attendance_date';
                        if(frm.fields_dict['from_date']) target = 'from_date';
                        
                        frm.set_value(target, r.message);
                        frappe.show_alert({message: "📅 Synced to Gregorian", indicator: "green"});
                    }
                }
            });
        }
    }
});

function update_ethiopian(frm, fieldname) {
    if (frm.doc[fieldname]) {
        frappe.call({
            method: "ethiopia_compliance.utils.get_ec_date",
            args: { date: frm.doc[fieldname] },
            callback: function(r) {
                if (r.message && r.message !== frm.doc.ethiopian_date) {
                    frm.set_value('ethiopian_date', r.message);
                }
            }
        });
    }
}
    """

    for dt in target_doctypes:
        script_name = f"EC Sync - {dt}"
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
        print(f"✔ Logic connected for: {dt}")

    # ====================================================
    # 4. ADD ETHIOPIAN MONTHS (For Reporting)
    # ====================================================
    print("--- 🗓 ADDING ETHIOPIAN MONTHS TO CALENDAR ---")
    
    fiscal_year_name = "2017 E.C."
    company_name = "BESPO"  # <--- CRITICAL FIX: Bind to specific company
    
    # Check if Company exists to avoid errors
    if not frappe.db.exists("Company", company_name):
        # Fallback to default company if BESPO isn't the exact ID
        company_name = frappe.defaults.get_user_default("Company")

    if not frappe.db.exists("Fiscal Year", fiscal_year_name):
        fy = frappe.get_doc({
            "doctype": "Fiscal Year",
            "year": fiscal_year_name,
            "year_start_date": "2024-09-11",
            "year_end_date": "2025-09-10",
            "disabled": 0
        })
        
        # Link to Company to allow overlap
        fy.append("companies", {"company": company_name})
        
        fy.insert(ignore_permissions=True)
        print(f"✔ Created Fiscal Year: {fiscal_year_name} for {company_name}")

    frappe.db.commit()
    print("--- ✅ SUCCESS: SYSTEM IS NOW DUAL-CALENDAR ---")
    print("👉 Reload your browser to see the 'Ethiopian Date' on all forms.")

