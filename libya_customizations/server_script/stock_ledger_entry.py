import frappe
from frappe.utils import now_datetime

def update_item_price(doc, method=None):

    values = get_valuation_rate_and_qty(doc.item_code, doc.production_year)
    values["modified"] = now_datetime()
    
    frappe.db.sql(
        """
        UPDATE `tabItem Price`
        SET stock_valuation_rate = %(stock_valuation_rate)s,
            stock_qty = %(stock_qty)s,
            available_qty = %(available_qty)s,
            modified = %(modified)s
        WHERE item_code = %(item_code)s
            AND IFNULL(production_year, '') = IFNULL(%(production_year)s, '')
        """, values,
    )


def get_valuation_rate_and_qty(item_code, production_year):

    avg_rate = frappe.db.sql("""
        SELECT SUM(stock_value_difference) / SUM(actual_qty)
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s AND is_cancelled = 0
    """, (item_code,))[0][0]

    # Get Stock Qty (based on item_code + production_year)
    stock_qty = frappe.db.sql("""
        SELECT IFNULL(SUM(actual_qty), 0)
        FROM `tabStock Ledger Entry`
        WHERE is_cancelled = 0 AND item_code = %s AND IFNULL(production_year, '') = IFNULL(%s, '')
    """, (item_code, production_year))[0][0]

    qty_to_deliver = frappe.db.sql("""
        WITH reserved_qty AS (
            SELECT so.name, IF(SUM(soi.qty - soi.delivered_qty) > 0, SUM(soi.qty - soi.delivered_qty), 0) AS qty_to_deliver
            FROM `tabSales Order Item` soi
            INNER JOIN `tabSales Order` so ON soi.parent = so.name
            WHERE soi.docstatus = 1 AND so.docstatus = 1 AND so.status NOT IN ('Completed', 'Closed') AND soi.qty - soi.delivered_qty > 0
            AND soi.item_code = %s AND IFNULL(soi.production_year, '') = IFNULL(%s, '')
        )
        SELECT IFNULL(SUM(qty_to_deliver), 0)
        FROM reserved_qty
    """, (item_code, production_year))[0][0]

    available_qty = stock_qty - qty_to_deliver

    return {
        "stock_valuation_rate": avg_rate or 0,
        "stock_qty": stock_qty or 0,
        "available_qty": available_qty or 0,
        "item_code": item_code,
        "production_year": production_year
    }