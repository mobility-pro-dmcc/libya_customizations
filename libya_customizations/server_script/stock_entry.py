import frappe

def after_stock_entry_insert(doc, method):
    warehouse_user = frappe.get_cached_value('Warehouse', doc.to_warehouse, 'warehouse_user')
    if warehouse_user:
        frappe.share.add(
            'Stock Entry',
            doc.name,
            warehouse_user,
            read=1,
            write=1
        )

