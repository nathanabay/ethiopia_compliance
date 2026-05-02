
frappe.query_reports["TASS Purchase Excel Export"] = {
    "filters": [
        {"fieldname": "company", "label": __("Company"), "fieldtype": "Link", "options": "Company", "default": frappe.defaults.get_user_default("Company"), "reqd": 1},
        {"fieldname": "from_date", "label": __("From Date"), "fieldtype": "Date", "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1), "reqd": 1},
        {"fieldname": "to_date", "label": __("To Date"), "fieldtype": "Date", "default": frappe.datetime.get_today(), "reqd": 1},
        {"fieldname": "use_ethiopian_calendar", "label": __("Use Ethiopian Calendar"), "fieldtype": "Check", "default": 0}
    ],
    "onload": function(report) {
        report.page.add_inner_button(__("Download for Darash"), function() {
            frappe.call({
                method: "frappe.desk.query_report.run",
                args: {
                    report_name: report.report_name,
                    filters: report.get_filter_values()
                },
                freeze: true,
                freeze_message: __("Preparing Darash export..."),
                callback: function(r) {
                    if (!r.message || !r.message.result || !r.message.result.length) {
                        frappe.msgprint(__("No data to export"));
                        return;
                    }
                    var columns = r.message.columns;
                    var data = r.message.result;
                    var header = columns.map(function(c) {
                        return '"' + c.label + '"';
                    }).join(",");
                    var rows = data.map(function(row) {
                        return columns.map(function(c) {
                            var val = row[c.fieldname];
                            if (val == null) val = "";
                            val = String(val).replace(/"/g, '""');
                            return '"' + val + '"';
                        }).join(",");
                    });
                    var csv = header + "\n" + rows.join("\n");
                    frappe.download_csv(csv, report.report_name.replace(/ /g, "_") + "_Darash.csv");
                    frappe.show_alert(__("Darash export ready"), 5);
                }
            });
        });
    }
};
