import frappe
from libya_customizations.server_script.purchase_invoice import update_status

def execute():
    print("Updating Payment Status for Purchase Invoices...")
    for pi in frappe.get_all("Purchase Invoice", fields=["name", "is_paid", "is_return", "is_opening", "docstatus"]):
        method = pi.docstatus == 2 and "before_cancel" or "before_submit"
        frappe.db.set_value("Purchase Invoice", pi.name, "custom_payment_status", update_status(pi, method))
        print("Updated Payment Status for Purchase Invoice: ", pi.name)
    print("Payment Status Update Completed.")