// Copyright (c) 2026, Bespo and contributors
// For license information, please see license.txt

/*
Purchase Order Client Script — TIN Warning

Phase 1.7: On Purchase Order before_save, if the supplier does not have a
valid TIN on file, display a frappe.msgprint warning that a 30% punitive
WHT rate will be applied.

Hooked via: Custom Script — Purchase Order (Client Script DocType fixture)
*/

frappe.ui.form.on('Purchase Order', {
    before_save: function(frm) {
        if (!frm.doc.supplier) {
            return;
        }

        // Fetch supplier TIN status if not already loaded
        frappe.call({
            method: 'ethiopia_compliance.utils.tin_validator.is_supplier_tin_valid',
            args: {
                supplier_name: frm.doc.supplier
            },
            callback: function(r) {
                if (r.message === false || r.message === 'false') {
                    frappe.msgprint({
                        title: __('WHT Compliance Warning'),
                        indicator: 'orange',
                        message: __(
                            'Supplier <strong>{0}</strong> does not have a valid TIN on file. '
                            + 'A <strong>30% punitive WHT rate</strong> will be applied to this '
                            + 'Purchase Order under <strong>Proclamation No. 1395/2017 Art. 97</strong>. '
                            + '<br><br>'
                            + 'Please collect and record the supplier\'s correct TIN '
                            + 'to avoid this penalty.'
                        ).format(frm.doc.supplier),
                        wide: true
                    });
                }
            }
        });
    }
});