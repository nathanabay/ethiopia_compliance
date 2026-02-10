import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def run():
    print("--- Adding Commercial Code 1243/2021 Fields ---")
    
    custom_fields = {
        "Company": [
            {
                "fieldname": "custom_trade_name",
                "label": "Trade Name",
                "fieldtype": "Data",
                "insert_after": "company_name",
                "description": "Distinct from Company Name (Art. 5 Commercial Code)."
            },
            {
                "fieldname": "custom_auditor_name",
                "label": "External Auditor",
                "fieldtype": "Data",
                "insert_after": "tax_id"
            },
            {
                "fieldname": "custom_auditor_term_end",
                "label": "Auditor Term End",
                "fieldtype": "Date",
                "insert_after": "custom_auditor_name",
                "description": "Auditors serve for 3 years max per term (Art. 344)."
            },
            {
                "fieldname": "custom_nominee_name",
                "label": "Nominee (For OPPLC)",
                "fieldtype": "Data",
                "insert_after": "custom_auditor_term_end",
                "description": "Required for One Person PLCs (Art. 506)."
            }
        ]
    }
    
    create_custom_fields(custom_fields, update=True)
    print("✔ Commercial Code Fields Created")

