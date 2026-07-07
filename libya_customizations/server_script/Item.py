import frappe
def after_insert_item(doc, method):
    doc = frappe.get_doc(doc)
    price_lists = frappe.db.get_list("Price List", {"selling": 1}, ignore_permissions=True)
    for selling_price_list in price_lists:
        item_price = frappe.db.get_value("Item Price", {"item_code": doc.item_code, "price_list": selling_price_list.name})
        if not item_price:
            item_price_doc = frappe.get_doc({
                "doctype": "Item Price",
                "item_code": doc.item_code,
                "price_list": selling_price_list.name,
                "price_list_rate": 0,
                "selling": 1,
                "item_name": doc.item_name,
                "brand": doc.brand,
                'item_description': doc.description
            })
            item_price_doc.insert(ignore_permissions=True)

def after_update_item(doc, method):
    doc = frappe.get_doc(doc)
    price_lists = frappe.db.get_list("Price List", {"selling": 1}, ignore_permissions=True)
    for selling_price_list in price_lists:
        item_price = frappe.db.get_value("Item Price", {"item_code": doc.item_code, "price_list": selling_price_list.name})
        if item_price:
            existing_item_price = frappe.get_doc('Item Price', item_price)
            existing_item_price.update({
                "item_name": doc.item_name,
                "brand": doc.brand,
                'item_description': doc.description
            })
            existing_item_price.save(ignore_permissions=True)
    _update_item_default_income_account(doc)

def _update_item_default_income_account(doc):
    company = frappe.db.get_default('Company')
    sales_account = frappe.db.get_value('Company', company, 'default_income_account')

    if doc.item_defaults:
        doc.item_defaults[0].income_account = sales_account
    else:
        doc.append('item_defaults', {
            'company': company,
            'income_account': sales_account
        })
        doc.save()