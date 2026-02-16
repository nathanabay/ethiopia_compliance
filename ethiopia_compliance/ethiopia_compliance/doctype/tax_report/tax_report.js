frappe.ui.form.on('Tax Report', {
    refresh: function (frm) {
        if (!frm.doc.__islocal && frm.doc.status !== 'Submitted') {
            frm.add_custom_button(__('Generate Report'), function () {
                generate_report(frm);
            }).addClass('btn-primary');
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
        // Auto-set dates based on period type
        if (frm.doc.period_type === 'Monthly' && !frm.doc.from_date) {
            let today = frappe.datetime.get_today();
            let month_start = frappe.datetime.month_start(today);
            let month_end = frappe.datetime.month_end(today);

            frm.set_value('from_date', month_start);
            frm.set_value('to_date', month_end);
        }
    }
});

function generate_report(frm) {
    frappe.show_alert({
        message: __('Generating report...'),
        indicator: 'blue'
    });

    frappe.call({
        method: 'ethiopia_compliance.ethiopia_compliance.doctype.tax_report.tax_report.generate_report',
        args: {
            docname: frm.doc.name
        },
        callback: function (r) {
            if (r.message) {
                frm.reload_doc();
                frappe.show_alert({
                    message: __('Report generated successfully'),
                    indicator: 'green'
                });
            }
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
