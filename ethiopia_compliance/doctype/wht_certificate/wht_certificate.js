// Copyright (c) 2026, Bespo and contributors
// For license information, please see license.txt

frappe.ui.form.on('WHT Certificate', {
    refresh: function (frm) {
        if (frm.doc.docstatus === 0 && !frm.is_new()) {
            frm.add_custom_button(__('Generate Data'), function () {
                frm.call({
                    method: 'generate_certificate_data',
                    doc: frm.doc,
                    callback: function (r) {
                        frm.refresh();
                        frappe.msgprint(__('Certificate data generated successfully'));
                    }
                });
            });
        }

        // Add print button
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Print'), function () {
                frm.print_doc();
            });
        }
    },

    supplier: function (frm) {
        // Auto-fetch supplier TIN
        if (frm.doc.supplier) {
            frappe.db.get_value('Supplier', frm.doc.supplier, 'tax_id', (r) => {
                if (r && r.tax_id) {
                    frm.set_value('supplier_tin', r.tax_id);
                }
            });
        }
    }
});
