import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    print("Setting up Ethiopian Compliance Module...")
    create_income_tax_slabs()
    create_standard_fields()
    frappe.db.commit()

def create_income_tax_slabs():
    slab_name = "Ethiopia Tax 2025/2026"
    if not frappe.db.exists("Income Tax Slab", slab_name):
        doc = frappe.get_doc({
            "doctype": "Income Tax Slab",
            "name": slab_name,
            "currency": "ETB",
            "effective_from": "2025-07-08",
            "allow_tax_exemption": 1,
            "slabs": [
                {"from_amount": 0, "to_amount": 2000, "percent_deduction": 0},
                {"from_amount": 2001, "to_amount": 4000, "percent_deduction": 15},
                {"from_amount": 4001, "to_amount": 7000, "percent_deduction": 20},
                {"from_amount": 7001, "to_amount": 10000, "percent_deduction": 25},
                {"from_amount": 10001, "to_amount": 14000, "percent_deduction": 30},
                {"from_amount": 14001, "to_amount": 9999999, "percent_deduction": 35}
            ]
        })
        doc.insert(ignore_permissions=True)

def create_standard_fields():
    custom_fields = {
        "Company": [
            {"fieldname": "custom_vat_reg_number", "label": "VAT Registration Number", "fieldtype": "Data", "insert_after": "tax_id"}
        ],
        "Employee": [
            {"fieldname": "custom_pension_number", "label": "Pension Number", "fieldtype": "Data", "insert_after": "tax_id", "unique": 1},
            {"fieldname": "custom_mothers_name", "label": "Mother's Name", "fieldtype": "Data", "insert_after": "last_name"},
            {"fieldname": "custom_kebele", "label": "Kebele", "fieldtype": "Data", "insert_after": "current_address"},
            {"fieldname": "custom_house_number", "label": "House Number", "fieldtype": "Data", "insert_after": "custom_kebele"}
        ],
        "Supplier": [
            {"fieldname": "custom_wht_eligible", "label": "WHT Eligible (2%)", "fieldtype": "Check", "insert_after": "tax_id", "default": 0},
            {"fieldname": "custom_vat_registered", "label": "VAT Registered", "fieldtype": "Check", "insert_after": "custom_wht_eligible", "default": 1}
        ],
        "Sales Invoice": [
            {"fieldname": "custom_fs_number", "label": "FS Number", "fieldtype": "Data", "insert_after": "taxes_and_charges", "description": "Fiscal Signature from Printer"},
            {"fieldname": "custom_fiscal_machine_no", "label": "Fiscal Machine No", "fieldtype": "Data", "insert_after": "custom_fs_number"}
        ],
        "Purchase Invoice": [
            {"fieldname": "custom_supplier_tin", "label": "Supplier TIN", "fieldtype": "Data", "insert_after": "supplier_address", "fetch_from": "supplier.tax_id"},
            {"fieldname": "custom_wht_receipt_no", "label": "WHT Receipt Number", "fieldtype": "Data", "insert_after": "taxes_and_charges"}
        ],
        "Item": [
            {"fieldname": "custom_hs_code", "label": "HS Code", "fieldtype": "Data", "insert_after": "item_group"}
        ]
    }
    create_custom_fields(custom_fields, update=True)
