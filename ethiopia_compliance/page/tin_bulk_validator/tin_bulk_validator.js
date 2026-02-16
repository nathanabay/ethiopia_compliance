frappe.pages['tin-bulk-validator'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'TIN Bulk Validator',
        single_column: true
    });

    let bulk_validator = new TINBulkValidator(page);
    bulk_validator.show();
};

class TINBulkValidator {
    constructor(page) {
        this.page = page;
        this.parent = $(this.page.body);
        this.results = [];
    }

    show() {
        this.render_ui();
        this.bind_events();
    }

    render_ui() {
        this.parent.html(`
            <div class="tin-bulk-validator">
                <div class="row">
                    <div class="col-md-12">
                        <div class="form-group">
                            <label>Enter TINs (one per line or comma-separated)</label>
                            <textarea class="form-control" id="tin-input" rows="10" 
                                placeholder="0012345678&#10;0023456789&#10;0034567890"></textarea>
                        </div>
                        <button class="btn btn-primary" id="validate-btn">
                            <i class="fa fa-check"></i> Validate TINs
                        </button>
                        <button class="btn btn-secondary" id="clear-btn">
                            <i class="fa fa-times"></i> Clear
                        </button>
                    </div>
                </div>
                <div class="row" style="margin-top: 20px;">
                    <div class="col-md-12">
                        <div id="results-container"></div>
                    </div>
                </div>
            </div>
        `);
    }

    bind_events() {
        const me = this;

        this.parent.find('#validate-btn').on('click', function () {
            me.validate_tins();
        });

        this.parent.find('#clear-btn').on('click', function () {
            me.clear();
        });
    }

    validate_tins() {
        let input = this.parent.find('#tin-input').val();
        if (!input) {
            frappe.msgprint('Please enter TINs to validate');
            return;
        }

        // Parse TINs from input (handle newlines and commas)
        let tins = input.split(/[\\n,]+/).map(t => t.trim()).filter(t => t.length > 0);

        if (tins.length === 0) {
            frappe.msgprint('No valid TINs found');
            return;
        }

        frappe.show_alert({
            message: `Validating ${tins.length} TINs...`,
            indicator: 'blue'
        });

        frappe.call({
            method: 'ethiopia_compliance.utils.tin_validator.bulk_validate_tins',
            args: { tin_list: tins },
            callback: (r) => {
                if (r.message) {
                    this.results = r.message;
                    this.show_results();
                }
            }
        });
    }

    show_results() {
        if (this.results.length === 0) return;

        let valid_count = this.results.filter(r => r.valid).length;
        let invalid_count = this.results.length - valid_count;

        let html = `
            <div class="results-summary">
                <h4>Validation Results</h4>
                <p>
                    <span class="badge badge-success">${valid_count} Valid</span>
                    <span class="badge badge-danger">${invalid_count} Invalid</span>
                    <span class="badge badge-info">${this.results.length} Total</span>
                </p>
            </div>
            <table class="table table-bordered">
                <thead>
                    <tr>
                        <th width="5%">#</th>
                        <th width="20%">TIN</th>
                        <th width="10%">Status</th>
                        <th width="15%">Type</th>
                        <th width="50%">Message</th>
                    </tr>
                </thead>
                <tbody>
        `;

        this.results.forEach((result, idx) => {
            let status_class = result.valid ? 'success' : 'danger';
            let status_icon = result.valid ? '✓' : '✗';

            html += `
                <tr class="table-${status_class}">
                    <td>${idx + 1}</td>
                    <td><code>${result.tin}</code></td>
                    <td><span class="badge badge-${status_class}">${status_icon}</span></td>
                    <td>${result.type}</td>
                    <td>${result.message}</td>
                </tr>
            `;
        });

        html += `
                </tbody>
            </table>
            <div style="margin-top: 10px;">
                <button class="btn btn-secondary" id="export-results">
                    <i class="fa fa-download"></i> Export to CSV
                </button>
            </div>
        `;

        this.parent.find('#results-container').html(html);

        // Bind export button
        const me = this;
        this.parent.find('#export-results').on('click', function () {
            me.export_to_csv();
        });
    }

    export_to_csv() {
        let csv = 'TIN,Status,Type,Message\\n';
        this.results.forEach(r => {
            let status = r.valid ? 'Valid' : 'Invalid';
            csv += `"${r.tin}","${status}","${r.type}","${r.message}"\\n`;
        });

        // Download CSV
        let blob = new Blob([csv], { type: 'text/csv' });
        let url = URL.createObjectURL(blob);
        let a = document.createElement('a');
        a.href = url;
        a.download = 'tin_validation_results.csv';
        a.click();

        frappe.show_alert({
            message: 'Results exported to CSV',
            indicator: 'green'
        });
    }

    clear() {
        this.parent.find('#tin-input').val('');
        this.parent.find('#results-container').html('');
        this.results = [];
    }
}
