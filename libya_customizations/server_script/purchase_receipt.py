import frappe
def on_submit(doc, method):
    doctype = doc.doctype
    docname = doc.name
    landed_cost_voucher = frappe.new_doc("Landed Cost Voucher")

    details = frappe.db.get_value(doctype, docname, ["supplier", "company", "base_grand_total", "title"], as_dict=1)

    landed_cost_voucher.company = details.company
    
    landed_cost_voucher.receipt_title = details.title

    landed_cost_voucher.append(
        "purchase_receipts",
        {
            "receipt_document_type": doctype,
            "receipt_document": docname,
            "grand_total": details.base_grand_total,
            "supplier": details.supplier,
        },
    )

    landed_costs = []
    if(doc.freight_amount):
        landed_costs.append({
            "expense_account":doc.freight_account,
            "account_currency": doc.freight_account_currency,
            "exchange_rate": doc.freight_exchange_rate,
            "description": "Freight",
            "amount": doc.freight_amount
        })
        
    if(doc.inspection_amount):
        landed_costs.append({
            "expense_account":doc.inspection_account,
            "account_currency": doc.inspection_account_currency,
            "exchange_rate": doc.inspection_exchange_rate,
            "description": "Inspection",
            "amount": doc.inspection_amount
        })
        
    if(doc.foreign_bank_charges_amount):
        landed_costs.append({
            "expense_account":doc.foreign_bank_charges_account,
            "account_currency": doc.foreign_bank_charges_account_currency,
            "exchange_rate": doc.foreign_bank_charges_exchange_rate,
            "description": "Foreign Bank Charges",
            "amount": doc.foreign_bank_charges_amount
        })
        
    if(doc.local_bank_charges_amount):
        landed_costs.append({
            "expense_account":doc.local_bank_charges_account,
            "description": "Local Bank Charges",
            "amount": doc.local_bank_charges_amount
        })
           
    if(doc.other_foreign_charges_amount):
        landed_costs.append({
            "expense_account":doc.other_foreign_charges_account,
            "account_currency": doc.other_foreign_charges_account_currency,
            "exchange_rate": doc.other_foreign_charges_exchange_rate,
            "description": "Other Foreign Charges",
            "amount": doc.other_foreign_charges_amount
        })
        
    if(doc.other_local_charges_amount):
        landed_costs.append({
            "expense_account":doc.other_local_charges_account,
            "description": "Other Local Charges",
            "amount": doc.other_local_charges_amount
        })

    landed_costs.append({
        "expense_account":doc.clearance_account,
        "description": "Clearance",
        "amount": doc.clearance_amount
        })
    
    landed_costs.append({
        "expense_account":doc.transport_account,
        "description": "Transport",
        "amount": doc.transport_amount
        })

    landed_cost_voucher.get_items_from_purchase_receipts()
    landed_cost_voucher.update({
        "taxes": landed_costs
    })
    landed_cost_voucher.insert(ignore_permissions=True)
    landed_cost_voucher.submit()


def on_update_after_submit(doc, method):
    landed_cost_voucher_name = frappe.db.get_value("Landed Cost Purchase Receipt", {"receipt_document_type": "Purchase Receipt", "receipt_document": doc.name}, "parent")
    doctype = "Landed Cost Voucher"
    status = 0
    d = frappe.get_doc(doctype, landed_cost_voucher_name)
    tables = [item for item in d.as_dict().values() if isinstance(item, list)]
    frappe.db.set_value(doctype, d.name, "docstatus", status)
    
    for row in tables:
        for child in row:
            frappe.db.set_value(child.doctype, child.name, "docstatus", status)
    d.reload()
    landed_costs = []

    if(doc.freight_amount):
        landed_costs.append({
            "expense_account":doc.freight_account,
            "account_currency": doc.freight_account_currency,
            "exchange_rate": doc.freight_exchange_rate,
            "description": "Freight",
            "amount": doc.freight_amount
        })
        
    if(doc.inspection_amount):
        landed_costs.append({
            "expense_account":doc.inspection_account,
            "account_currency": doc.inspection_account_currency,
            "exchange_rate": doc.inspection_exchange_rate,
            "description": "Inspection",
            "amount": doc.inspection_amount
        })
        
    if(doc.foreign_bank_charges_amount):
        landed_costs.append({
            "expense_account":doc.foreign_bank_charges_account,
            "account_currency": doc.foreign_bank_charges_account_currency,
            "exchange_rate": doc.foreign_bank_charges_exchange_rate,
            "description": "Foreign Bank Charges",
            "amount": doc.foreign_bank_charges_amount
        })
        
    if(doc.local_bank_charges_amount):
        landed_costs.append({
            "expense_account":doc.local_bank_charges_account,
            "description": "Local Bank Charges",
            "amount": doc.local_bank_charges_amount
        })
    
    if(doc.other_foreign_charges_amount):
        landed_costs.append({
            "expense_account":doc.other_foreign_charges_account,
            "account_currency": doc.other_foreign_charges_account_currency,
            "exchange_rate": doc.other_foreign_charges_exchange_rate,
            "description": "Other Foreign Charges",
            "amount": doc.other_foreign_charges_amount
        })
        
    if(doc.other_local_charges_amount):
        landed_costs.append({
            "expense_account":doc.other_local_charges_account,
            "description": "Other Local Charges",
            "amount": doc.other_local_charges_amount
        })
            
    landed_costs.append({
        "expense_account":doc.clearance_account,
        "description": "Clearance",
        "amount": doc.clearance_amount
        })
    
    landed_costs.append({
        "expense_account":doc.transport_account,
        "description": "Transport",
        "amount": doc.transport_amount
        })
    # d = frappe.get_doc(doctype, dd)
    d.taxes = []
    d.set("taxes", landed_costs)
    d.save(ignore_permissions=True)
    d.submit()
