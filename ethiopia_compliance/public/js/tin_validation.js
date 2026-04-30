// TIN Validation Client Script
// Provides real-time validation for TIN fields

frappe.provide('ethiopia_compliance.tin_validator');

ethiopia_compliance.tin_validator = {
    validate_tin: function (tin_number, callback) {
        if (!tin_number) {
            callback({ valid: false, message: 'TIN is required', type: 'Unknown' });
            return;
        }

        frappe.call({
            method: 'ethiopia_compliance.utils.tin_validator.validate_tin_api',
            args: { tin_number: tin_number },
            callback: function (r) {
                if (r.message) {
                    callback(r.message);
                } else {
                    callback({ valid: false, message: __('Validation failed'), type: 'Unknown' });
                }
            },
            error: function () {
                callback({ valid: false, message: __('Server error'), type: 'Unknown' });
            }
        });
    },

    show_validation_message: function (frm, result, fieldname) {
        fieldname = fieldname || 'tax_id';
        let msg_type = frappe.utils.escape_html(result.type || '');
        let msg_text = frappe.utils.escape_html(result.message || '');

        if (result.valid) {
            frappe.show_alert({
                message: __('Valid {0} TIN', [msg_type]),
                indicator: 'green'
            });
            frm.set_df_property(fieldname, 'description',
                '<span style="color: green;">&#10003; Valid ' + msg_type + ' TIN</span>');
        } else {
            frappe.show_alert({
                message: __(msg_text),
                indicator: 'red'
            });
            frm.set_df_property(fieldname, 'description',
                '<span style="color: red;">&#10007; ' + msg_text + '</span>');
        }
    },

    validate_and_show: function (frm, fieldname) {
        fieldname = fieldname || 'tax_id';
        let tin = frm.doc[fieldname];

        if (!tin) return;

        this.validate_tin(tin, (result) => {
            this.show_validation_message(frm, result, fieldname);
        });
    }
};

// Auto-attach to Supplier
frappe.ui.form.on('Supplier', {
    tax_id: function (frm) {
        ethiopia_compliance.tin_validator.validate_and_show(frm, 'tax_id');
    }
});

// Auto-attach to Customer
frappe.ui.form.on('Customer', {
    tax_id: function (frm) {
        ethiopia_compliance.tin_validator.validate_and_show(frm, 'tax_id');
    }
});

// Auto-attach to Employee
frappe.ui.form.on('Employee', {
    tax_id: function (frm) {
        ethiopia_compliance.tin_validator.validate_and_show(frm, 'tax_id');
    }
});

// Auto-attach to Company
frappe.ui.form.on('Company', {
    tax_id: function (frm) {
        ethiopia_compliance.tin_validator.validate_and_show(frm, 'tax_id');
    }
});
