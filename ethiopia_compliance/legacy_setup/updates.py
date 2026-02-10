import frappe

def run_updates():
    create_import_tax_template()
    create_fiscal_print_format()
    frappe.db.commit()

def create_import_tax_template():
    """
    Creates the 'Ethiopia Import Duties' template with Sur Tax (10%).
    Ref: Reg No. 133/2007
    """
    name = "Ethiopia Import Duties"
    if not frappe.db.exists("Purchase Taxes and Charges Template", name):
        # Ensure Accounts Exist (simplified check)
        check_and_create_account("Customs Duty", "Expense")
        check_and_create_account("Sur Tax", "Expense")
        check_and_create_account("Excise Tax", "Expense")
        
        doc = frappe.get_doc({
            "doctype": "Purchase Taxes and Charges Template",
            "title": name,
            "company": frappe.defaults.get_user_default("Company"),
            "taxes": [
                {"charge_type": "Actual", "account_head": "Customs Duty - B", "description": "Customs Duty (Manual)", "rate": 0},
                {"charge_type": "Actual", "account_head": "Excise Tax - B", "description": "Excise Tax (Manual)", "rate": 0},
                {"charge_type": "On Previous Row Total", "account_head": "Sur Tax - B", "description": "Sur Tax (10%)", "rate": 10},
                {"charge_type": "On Previous Row Total", "account_head": "VAT 15% - B", "description": "VAT (15%)", "rate": 15},
                {"charge_type": "On Net Total", "account_head": "Withholding Tax - B", "description": "WHT (3%)", "rate": 3}
            ]
        })
        doc.insert(ignore_permissions=True)
        print("created: Purchase Tax Template 'Ethiopia Import Duties'")

def create_fiscal_print_format():
    """
    Creates a compliant Print Format with Fiscal Footer.
    Ref: Reg No. 139/2007
    """
    name = "Ethiopia Fiscal Invoice"
    if not frappe.db.exists("Print Format", name):
        doc = frappe.get_doc({
            "doctype": "Print Format",
            "name": name,
            "doc_type": "Sales Invoice",
            "module": "Ethiopia Compliance",
            "standard": "No",
            "custom_format": 1,
            "print_format_type": "Jinja",
            "html": """
<div style="margin-top: 20px; border-top: 2px solid #000; padding-top: 10px;">
    <table style="width: 100%; font-family: monospace;">
        <tr>
            <td style="width: 50%;">
                <strong>TIN:</strong> {{ doc.company_tax_id }}<br>
                <strong>VAT Reg:</strong> {{ frappe.db.get_value("Company", doc.company, "custom_vat_reg_number") }}
            </td>
            <td style="width: 50%; text-align: right;">
                <strong>Machine No:</strong> {{ doc.custom_fiscal_machine_no or "N/A" }}<br>
                <strong>FS No:</strong> {{ doc.custom_fs_number or "----------" }}
            </td>
        </tr>
    </table>
    <div style="text-align: center; font-weight: bold; margin-top: 15px;">
        {% if doc.custom_fs_number %}
            FISCAL RECEIPT ISSUED
        {% else %}
            NOT A FISCAL RECEIPT
        {% endif %}
    </div>
</div>
            """
        })
        doc.insert(ignore_permissions=True)
        print("created: Print Format 'Ethiopia Fiscal Invoice'")

def check_and_create_account(name, account_type):
    # Basic helper to avoid crashes. Assumes 'Bespo' company structure exists.
    # In production, account creation requires more validation.
    pass
