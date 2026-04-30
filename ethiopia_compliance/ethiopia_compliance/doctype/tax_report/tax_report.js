frappe.ui.form.on('Tax Report', {
    refresh: function (frm) {
        if (!frm.doc.__islocal && frm.doc.status === 'Draft') {
            frm.add_custom_button(__('Generate Report'), function () {
                generate_report(frm);
            }).addClass('btn-primary');
        }

        if (frm.doc.status === 'Generating') {
            frm.dashboard.set_headline(__('Report is being generated...'), 'blue');
            // Auto-refresh every 3 seconds
            frm._poll_interval = setInterval(function () {
                frappe.db.get_value('Tax Report', frm.doc.name, 'status', (r) => {
                    if (r && r.status !== 'Generating') {
                        clearInterval(frm._poll_interval);
                        frm.reload_doc();
                    }
                });
            }, 3000);
        }

        if (frm.doc.report_data && frm.doc.status === 'Generated') {
            frm.add_custom_button(__('Export to Excel'), function () {
                export_to_excel(frm);
            });

            frm.add_custom_button(__('Export to PDF'), function () {
                frm.print_doc();
            });
        }

        // Set default company
        if (frm.doc.__islocal) {
            frm.set_value('company', frappe.defaults.get_user_default('Company'));
        }
    },

    period_type: function (frm) {
        if (frm.doc.period_type === 'Monthly' && !frm.doc.from_date) {
            let today = frappe.datetime.get_today();
            frm.set_value('from_date', frappe.datetime.month_start(today));
            frm.set_value('to_date', frappe.datetime.month_end(today));
        }
    }
});

function generate_report(frm) {
    frappe.call({
        method: 'ethiopia_compliance.ethiopia_compliance.doctype.tax_report.tax_report.generate_report',
        args: { docname: frm.doc.name },
        callback: function (r) {
            if (r.message) {
                frappe.show_alert({
                    message: __(r.message),
                    indicator: 'blue'
                });
                frm.reload_doc();
            }
        },
        error: function () {
            frappe.show_alert({
                message: __('Report generation failed'),
                indicator: 'red'
            });
        }
    });
}

function export_to_excel(frm) {
    let url = frappe.urllib.get_full_url(
        '/api/method/ethiopia_compliance.ethiopia_compliance.doctype.tax_report.tax_report.export_to_excel'
        + '?docname=' + encodeURIComponent(frm.doc.name)
    );
    window.open(url);
}
