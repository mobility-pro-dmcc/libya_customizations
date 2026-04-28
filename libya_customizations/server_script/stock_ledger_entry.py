import frappe
from frappe.utils import now_datetime

def update_item_price(doc, method=None):
    # for item in doc.items:
    values = get_valuation_rate_and_qty(doc.item_code)
    values["modified"] = now_datetime()
    values["pl"] = frappe.db.get_value("Warehouse", doc.warehouse, "default_selling_price_list")
    frappe.db.sql(
        """
        UPDATE `tabItem Price`
        SET stock_valuation_rate = %(stock_valuation_rate)s,
            stock_qty = %(stock_qty)s,
            modified = %(modified)s
        WHERE item_code = %(item_code)s AND price_list = %(pl)s
        """, values,
    )


def get_valuation_rate_and_qty(item_code):

    avg_rate = frappe.db.sql("""
        SELECT SUM(stock_value_difference) / SUM(actual_qty)
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s AND is_cancelled = 0
    """, (item_code,))[0][0]

    # Get Stock Qty (based on item_code + production_year)
    stock_qty = frappe.db.sql("""
        SELECT IFNULL(SUM(actual_qty), 0)
        FROM `tabStock Ledger Entry`
        WHERE is_cancelled = 0 AND item_code = %s
    """, (item_code))[0][0]

    return {
        "stock_valuation_rate": avg_rate or 0,
        "stock_qty": stock_qty or 0,
        "item_code": item_code,
    }