import frappe

def run():
    print("--- 🚑 REPAIRING BROKEN CLIENT SCRIPTS ---")

    # Find all scripts we created (two naming patterns)
    ec_sync_scripts = frappe.get_all("Client Script",
        filters={"name": ["like", "EC Sync%"]},
        fields=["name", "dt"]
    )
    calendar_sync_scripts = frappe.get_all("Client Script",
        filters={"name": ["like", "Ethiopian Calendar Sync%"]},
        fields=["name", "dt"]
    )

    all_scripts = ec_sync_scripts + calendar_sync_scripts
    print(f"Found {len(all_scripts)} scripts to repair...")

    for s in all_scripts:
        doctype = s.dt
        script_name = s.name
        is_simple_sync = script_name.startswith("Ethiopian Calendar Sync")

        if is_simple_sync:
            # Simple sync: posting_date <-> ethiopian_date (no picker widget)
            fixed_js = f"""
frappe.ui.form.on('{doctype}', {{
    posting_date: function(frm) {{
        if (frm.doc.posting_date) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_ec_date",
                args: {{ date: frm.doc.posting_date }},
                callback: function(r) {{
                    if (r.message && r.message !== frm.doc.ethiopian_date) {{
                        frm.set_value('ethiopian_date', r.message);
                    }}
                }}
            }});
        }}
    }},
    ethiopian_date: function(frm) {{
        if (frm.doc.ethiopian_date && frm.doc.ethiopian_date.length >= 8) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_gc_date",
                args: {{ ethiopian_date: frm.doc.ethiopian_date }},
                callback: function(r) {{
                    if (r.message) {{
                        frm.set_value('posting_date', r.message);
                        frappe.show_alert({{message: "Synced with Gregorian Calendar", indicator: "green"}});
                    }} else {{
                        frappe.msgprint("Invalid Ethiopian Date. Use DD-MM-YYYY format.");
                    }}
                }}
            }});
        }}
    }}
}});
"""
        else:
            # Enhanced sync: full calendar picker widget with all date fields
            fixed_js = f"""
frappe.ui.form.on('{doctype}', {{
    refresh: function(frm) {{
        // 1. Bind the "Focus" event to trigger the selector
        if (frm.fields_dict['ethiopian_date']) {{
            frm.fields_dict['ethiopian_date'].$input.on('click', function() {{
                if (!frm.selector_open) {{
                    show_ethiopian_selector(frm);
                }}
            }});
        }}

        // Auto-fill on load
        // Use different field names based on doctype
        let date_field = 'posting_date';
        if(frm.doc.transaction_date) date_field = 'transaction_date';
        if(frm.doc.attendance_date) date_field = 'attendance_date';
        if(frm.doc.date_of_joining) date_field = 'date_of_joining';
        if(frm.doc.date && !frm.doc.posting_date) date_field = 'date';

        if (frm.doc[date_field] && !frm.doc.ethiopian_date) {{
            frm.trigger(date_field);
        }}
    }},

    // 2. Standard Sync: Gregorian -> Ethiopian
    posting_date: function(frm) {{ sync_to_ethiopian(frm, 'posting_date'); }},
    transaction_date: function(frm) {{ sync_to_ethiopian(frm, 'transaction_date'); }},
    attendance_date: function(frm) {{ sync_to_ethiopian(frm, 'attendance_date'); }},
    date_of_joining: function(frm) {{ sync_to_ethiopian(frm, 'date_of_joining'); }},
    date: function(frm) {{ sync_to_ethiopian(frm, 'date'); }},

    // 3. Reverse Sync: Ethiopian -> Gregorian
    ethiopian_date: function(frm) {{
        if (frm.doc.ethiopian_date && frm.doc.ethiopian_date.length >= 8) {{
            frappe.call({{
                method: "ethiopia_compliance.utils.get_gc_date",
                args: {{ ethiopian_date: frm.doc.ethiopian_date }},
                callback: function(r) {{
                    if (r.message) {{
                        set_gregorian(frm, r.message);
                    }}
                }}
            }});
        }}
    }}
}});

// --- HELPER FUNCTIONS ---

function show_ethiopian_selector(frm) {{
    frm.selector_open = true;

    let d = new frappe.ui.Dialog({{
        title: '📅 Select Ethiopian Date',
        fields: [
            {{
                label: 'Year (E.C.)',
                fieldname: 'year',
                fieldtype: 'Int',
                default: 2017,
                reqd: 1
            }},
            {{
                label: 'Month',
                fieldname: 'month',
                fieldtype: 'Select',
                options: [
                    {{label: 'Meskerem (1)', value: '01'}},
                    {{label: 'Tikimt (2)', value: '02'}},
                    {{label: 'Hidar (3)', value: '03'}},
                    {{label: 'Tahsas (4)', value: '04'}},
                    {{label: 'Tir (5)', value: '05'}},
                    {{label: 'Yekatit (6)', value: '06'}},
                    {{label: 'Megabit (7)', value: '07'}},
                    {{label: 'Miazia (8)', value: '08'}},
                    {{label: 'Genbot (9)', value: '09'}},
                    {{label: 'Sene (10)', value: '10'}},
                    {{label: 'Hamle (11)', value: '11'}},
                    {{label: 'Nehase (12)', value: '12'}},
                    {{label: 'Pagume (13)', value: '13'}}
                ],
                default: '01',
                reqd: 1
            }},
            {{
                label: 'Day',
                fieldname: 'day',
                fieldtype: 'Select',
                options: Array.from({{length: 30}}, (_, i) => (i + 1).toString()),
                default: '1',
                reqd: 1
            }}
        ],
        primary_action_label: 'Set Date',
        primary_action: function(values) {{
            let day = values.day.toString().padStart(2, '0');
            let date_str = `${{day}}-${{values.month}}-${{values.year}}`;

            frm.set_value('ethiopian_date', date_str);
            d.hide();
            frm.selector_open = false;
        }},
        onhide: function() {{
            frm.selector_open = false;
        }}
    }});

    d.show();
}}

function sync_to_ethiopian(frm, fieldname) {{
    if (frm.doc[fieldname]) {{
        frappe.call({{
            method: "ethiopia_compliance.utils.get_ec_date",
            args: {{ date: frm.doc[fieldname] }},
            callback: function(r) {{
                if (r.message && r.message !== frm.doc.ethiopian_date) {{
                    frm.set_value('ethiopian_date', r.message);
                }}
            }}
        }});
    }}
}}

function set_gregorian(frm, date_val) {{
    let fields = ['posting_date', 'transaction_date', 'attendance_date', 'date_of_joining', 'date'];
    for (let f of fields) {{
        if (frm.fields_dict[f]) {{
            frm.set_value(f, date_val);
            break;
        }}
    }}
    frappe.show_alert({{message: "✅ Synced to Gregorian", indicator: "green"}});
}}
"""
        # Apply Fix
        frappe.db.set_value("Client Script", script_name, "script", fixed_js)
        print(f"✔ Fixed: {script_name}")

    frappe.db.commit()
    frappe.clear_cache()
    print("--- ✅ ALL SCRIPTS REPAIRED ---")
