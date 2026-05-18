import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    custom_fields = {
        "Accounts Settings": [
            {
                "fieldname": "custom_overdue_controller",
                "label": "Overdue Controller",
                "fieldtype": "Link",
                "insert_after": "over_billing_allowance",
                "options": "Role"   
            },
            {
                "fieldname": "custom_overdue_tolerance_amount",
                "label": "Overdue Tolerance Amount",
                "fieldtype": "Currency",
                "insert_after": "custom_overdue_controller",
                "options": "Company:default_currency"
            }
        ]
    }
    for doctype, fields in custom_fields.items():
        for field in fields:
            if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": field["fieldname"]}):
                print(f"[PATCH] {doctype}.{field['fieldname']} already exists – skipping")
            else:
                create_custom_fields({doctype: [field]})
                print(f"[PATCH] {doctype}.{field['fieldname']} created")

    print("[PATCH] Custom fields for Accounts Settings added")
