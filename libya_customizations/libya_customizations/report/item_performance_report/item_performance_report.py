# Copyright (c) 2026, Ahmed Zaytoon and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "fieldname": "item_code",
            "label": _("Item"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "item_name",
            "label": _("Item Name"),
            "fieldtype": "Data",
            "width": 290,
        },
        {
            "fieldname": "brand",
            "label": _("Brand"),
            "fieldtype": "Link",
            "options": "Brand",
            "width": 100,
        },
        {
            "fieldname": "sales_qty",
            "label": _("Sales Qty"),
            "fieldtype": "Int",
            "width": 120,
        },
        {
            "fieldname": "sales_amount",
            "label": _("Sales Amount"),
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "fieldname": "sales_cost",
            "label": _("Sales Cost"),
            "fieldtype": "Currency",
            "width": 140,
        },
        {
            "fieldname": "gross_profit",
            "label": _("Gross Profit"),
            "fieldtype": "Currency",
            "width": 130,
        },
        {
            "fieldname": "gpm",
            "label": _("Profit %"),
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "fieldname": "stock_qty",
            "label": _("Stock Qty"),
            "fieldtype": "Int",
            "width": 120,
        },
    ]


def get_data(filters):
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    branch = filters.get("branch")

    # Branch is optional — build conditional clauses
    branch_filter_sales = "AND cg.branch = %(branch)s" if branch else ""
    branch_filter_cogs  = "AND si_dn.branch = %(branch)s" if branch else ""
    branch_filter_stock = "AND w.branch = %(branch)s" if branch else ""

    # si_dn CTE: used to link stock ledger entries back to a branch.
    # When no branch is selected we still need it, but the branch join
    # in the cogs block becomes unrestricted.
    si_dn_branch_col = ", branch" if branch else ", NULL AS branch"

    query = f"""
        WITH
        item AS (
            SELECT
                name  AS item_code,
                item_name,
                brand
            FROM `tabItem`
        ),
        si_dn AS (
            SELECT
                si.name,
                cg.branch
            FROM `tabSales Invoice` si
            LEFT JOIN `tabCustomer Group` cg
                ON si.customer_group = cg.name
            WHERE si.docstatus = 1
              AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
            UNION ALL
            SELECT
                dn.name,
                cg.branch
            FROM `tabDelivery Note` dn
            LEFT JOIN `tabCustomer Group` cg
                ON dn.customer_group = cg.name
            WHERE dn.docstatus = 1
              AND dn.posting_date BETWEEN %(from_date)s AND %(to_date)s
        ),
        sales AS (
            SELECT
                si_item.item_code,
                SUM(si_item.qty)        AS qty,
                SUM(si_item.net_amount) AS net_amount
            FROM `tabSales Invoice Item` si_item
            INNER JOIN `tabSales Invoice` si
                ON si_item.parent = si.name
            LEFT JOIN `tabCustomer Group` cg
                ON si.customer_group = cg.name
            WHERE si_item.docstatus = 1
              AND si.docstatus = 1
              AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s
              {branch_filter_sales}
            GROUP BY si_item.item_code
        ),
        cogs AS (
            SELECT
                sle.item_code,
                SUM(sle.stock_value_difference) * -1 AS stock_value_difference
            FROM `tabStock Ledger Entry` sle
            LEFT JOIN si_dn
                ON sle.voucher_no = si_dn.name
            WHERE sle.is_cancelled = 0
              AND sle.voucher_type IN ('Sales Invoice', 'Delivery Note')
              AND sle.posting_date BETWEEN %(from_date)s AND %(to_date)s
              {branch_filter_cogs}
            GROUP BY sle.item_code
        ),
        stock AS (
            SELECT
                sle.item_code,
                SUM(sle.actual_qty) AS actual_qty
            FROM `tabStock Ledger Entry` sle
            INNER JOIN `tabWarehouse` w
                ON sle.warehouse = w.name
            WHERE sle.is_cancelled = 0
              AND sle.posting_date <= %(to_date)s
              {branch_filter_stock}
            GROUP BY sle.item_code
        )
        SELECT
            item.item_code,
            item.item_name,
            item.brand,
            IFNULL(sales.qty, 0)                                        AS sales_qty,
            IFNULL(sales.net_amount, 0)                                 AS sales_amount,
            IFNULL(cogs.stock_value_difference, 0)                      AS sales_cost,
            IFNULL(sales.net_amount, 0)
                - IFNULL(cogs.stock_value_difference, 0)                AS gross_profit,
            CONCAT(
                FORMAT(
                    ROUND(
                        (IFNULL(sales.net_amount, 0)
                            - IFNULL(cogs.stock_value_difference, 0))
                        / NULLIF(IFNULL(sales.net_amount, 0), 0) * 100,
                    1),
                1),
                '%%')                                                   AS gpm,
            IFNULL(stock.actual_qty, 0)                                 AS stock_qty
        FROM item
        LEFT JOIN sales ON item.item_code = sales.item_code
        LEFT JOIN cogs  ON item.item_code = cogs.item_code
        LEFT JOIN stock ON item.item_code = stock.item_code
        WHERE ABS(IFNULL(sales.qty, 0)) + IFNULL(stock.actual_qty, 0) > 0
        ORDER BY item.brand, IFNULL(sales.qty, 0) DESC
    """

    params = {
        "from_date": from_date,
        "to_date": to_date,
    }
    if branch:
        params["branch"] = branch

    data = frappe.db.sql(query, params, as_dict=True)
    return data