# Copyright (c) 2024, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from openpyxl import Workbook
from frappe.utils.file_manager import save_file
from frappe.utils import get_site_path

class PurchaseReceiptManagement(Document):
	pass

def production_year_filter(column, value):
	if value:
		return f'AND {column} = "{frappe.db.escape(value)}"'
	return f'AND ({column} IS NULL OR {column} = "")'

@frappe.whitelist()
def update_is_virtual(docname, virtual_receipt):
	frappe.db.set_value('Purchase Receipt', docname, 'virtual_receipt', virtual_receipt)
	frappe.db.commit()

@frappe.whitelist()
def export_selected_data(names):
	if isinstance(names, str):
		names = json.loads(names)
	if not isinstance(names, list):
		frappe.throw("Expected a list of names.")
	
	parent_fields = ["name", "title"]
	child_fields = ["brand", "item_code", "item_name", "production_year", "qty", "rate", "amount"]
	
	workbook = Workbook()
	sheet = workbook.active
	sheet.append(parent_fields + child_fields)

	for name in names:
		parent_doc = frappe.get_doc("Purchase Receipt", name)
		for index, child in enumerate(parent_doc.items):
			child_data = [getattr(child, field, "") for field in child_fields]
			if index == 0:
				row = [parent_doc.name, parent_doc.title] + child_data
			else:
				row = [""] * len(parent_fields) + child_data
			sheet.append(row)

	file_path = get_site_path("private", "files", "Purchase_Receipt_Export.xlsx")
	workbook.save(file_path)

	with open(file_path, "rb") as file:
		file_doc = save_file(
			"Purchase Receipt Export",
			file.read(),
			"File",
			frappe.session.user,
			is_private=1,
		)

	return file_doc.file_url

@frappe.whitelist()
def submit_receipt(docname, posting_date):
	if not docname:
		frappe.throw("docname cannot be null")
	purchase_receipt = frappe.get_doc("Purchase Receipt", docname)
	purchase_receipt.posting_date = posting_date
	purchase_receipt.virtual_receipt = 0
	purchase_receipt.flags.ignore_permissions = True
	purchase_receipt.submit()

@frappe.whitelist()
def get_values_for_validation(purchase_receipt):
	doc = frappe.get_doc("Purchase Receipt", purchase_receipt)
	entries = []

	for row in doc.items:
		production_filter = production_year_filter("production_year", row.production_year)

		sql = frappe.db.sql(f"""
			SELECT
				IF(sales_future.future_qty_to_deliver > purchase_future.future_balance,
					stock_actual.actual_balance - (sales_actual.actual_qty_to_deliver + (sales_future.future_qty_to_deliver - purchase_future.future_balance)),
					stock_actual.actual_balance - sales_actual.actual_qty_to_deliver) AS actual_available_qty,
				(stock_actual.actual_balance + purchase_future.future_balance) - (sales_actual.actual_qty_to_deliver + sales_future.future_qty_to_deliver) AS future_available_qty
			FROM
				(
					SELECT COALESCE(SUM(actual_qty), 0) AS actual_balance
					FROM `tabStock Ledger Entry`
					WHERE is_cancelled = 0
						AND item_code = "{frappe.db.escape(row.item_code)}"
						{production_filter}
						AND warehouse = "{frappe.db.escape(doc.set_warehouse)}"
				) stock_actual
			LEFT JOIN (
				SELECT COALESCE(SUM(purchase_receipt_item.qty), 0) AS future_balance
				FROM `tabPurchase Receipt Item` purchase_receipt_item
				INNER JOIN `tabPurchase Receipt` purchase_receipt ON purchase_receipt_item.parent = purchase_receipt.name
				WHERE purchase_receipt_item.docstatus = 0
					AND purchase_receipt.docstatus = 0
					AND purchase_receipt.virtual_receipt = 1
					AND purchase_receipt_item.item_code = "{frappe.db.escape(row.item_code)}"
					{production_filter}
					AND purchase_receipt_item.warehouse = "{frappe.db.escape(doc.set_warehouse)}"
			) purchase_future ON TRUE
			LEFT JOIN (
				SELECT COALESCE(SUM(qty_to_deliver), 0) AS actual_qty_to_deliver
				FROM (
					SELECT
						sales_order_item.item_code,
						sales_order_item.production_year,
						sales_order.set_warehouse,
						IF(SUM(sales_order_item.qty - sales_order_item.delivered_qty) > 0,
							SUM(sales_order_item.qty - sales_order_item.delivered_qty), 0) AS qty_to_deliver
					FROM `tabSales Order Item` sales_order_item
					INNER JOIN `tabSales Order` sales_order ON sales_order_item.parent = sales_order.name
					INNER JOIN `tabItem` item ON sales_order_item.item_code = item.name
					WHERE sales_order.docstatus = 1
						AND sales_order_item.docstatus = 1
						AND sales_order.status NOT IN ('Completed', 'Closed')
						AND sales_order.reservation_status NOT IN ('Reserve against Future Receipts')
						AND (sales_order_item.qty - sales_order_item.delivered_qty) > 0
						AND item.is_stock_item = 1
					GROUP BY sales_order_item.item_code, sales_order_item.production_year
				) sales_order_item
				WHERE item_code = "{frappe.db.escape(row.item_code)}"
					{production_filter}
					AND set_warehouse = "{frappe.db.escape(doc.set_warehouse)}"
			) sales_actual ON TRUE
			LEFT JOIN (
				SELECT COALESCE(SUM(qty_to_deliver), 0) AS future_qty_to_deliver
				FROM (
					SELECT
						sales_order_item.item_code,
						sales_order_item.production_year,
						IF(SUM(sales_order_item.qty - sales_order_item.delivered_qty) > 0,
							SUM(sales_order_item.qty - sales_order_item.delivered_qty), 0) AS qty_to_deliver
					FROM `tabSales Order Item` sales_order_item
					INNER JOIN `tabSales Order` sales_order ON sales_order_item.parent = sales_order.name
					INNER JOIN `tabItem` item ON sales_order_item.item_code = item.name
					WHERE sales_order.docstatus = 1
						AND sales_order_item.docstatus = 1
						AND sales_order.status NOT IN ('Completed', 'Closed')
						AND sales_order.reservation_status IN ('Reserve against Future Receipts')
						AND (sales_order_item.qty - sales_order_item.delivered_qty) > 0
						AND item.is_stock_item = 1
					GROUP BY sales_order_item.item_code, sales_order_item.production_year
				) sales_order_item
				WHERE item_code = "{frappe.db.escape(row.item_code)}"
					{production_filter}
					AND set_warehouse = "{frappe.db.escape(doc.set_warehouse)}"
			) sales_future ON TRUE
		""", as_dict=True)

		sql[0]["qty"] = row.qty
		sql[0]["item_code"] = row.item_name
		entries.append(sql[0])

	return entries

@frappe.whitelist()
def get_purchase_receipt_data(purchase_receipt):
	sql = """
	WITH purchase_receipt AS (
		SELECT
			name,
			posting_date,
			(freight_amount * freight_exchange_rate + inspection_amount * inspection_exchange_rate + clearance_amount +
			transport_amount + foreign_bank_charges_amount * foreign_bank_charges_exchange_rate + local_bank_charges_amount) / base_grand_total AS landed_cost_prorata
		FROM `tabPurchase Receipt`
		WHERE docstatus != 2
	),
	purchase_receipt_item AS (
		SELECT
			purchase_receipt_item.item_code,
			IFNULL(purchase_receipt_item.production_year, "") AS production_year,
			item.item_name,
			item.brand,
			purchase_receipt_item.docstatus,
			SUM(purchase_receipt_item.qty) AS qty,
			SUM(purchase_receipt_item.base_net_amount + purchase_receipt_item.item_tax_amount +
				(purchase_receipt_item.base_net_amount + purchase_receipt_item.item_tax_amount) * purchase_receipt.landed_cost_prorata) AS total_cost_amount
		FROM `tabPurchase Receipt Item` purchase_receipt_item
		INNER JOIN purchase_receipt ON purchase_receipt_item.parent = purchase_receipt.name
		INNER JOIN `tabItem` item ON purchase_receipt_item.item_code = item.name
		WHERE purchase_receipt_item.docstatus != 2
			AND purchase_receipt_item.parent = %s
		GROUP BY purchase_receipt_item.item_code, IFNULL(purchase_receipt_item.production_year, ""), item.item_name, item.brand
	),
	stock_ledger_entry_qty AS (
		SELECT item_code, IFNULL(production_year, "") AS production_year, SUM(actual_qty) AS actual_qty
		FROM `tabStock Ledger Entry`
		WHERE is_cancelled = 0
		GROUP BY item_code, IFNULL(production_year, "")
	),
	sales_order_item AS (
		SELECT sii.item_code, IFNULL(sii.production_year, "") AS production_year, SUM(sii.qty - sii.delivered_qty) AS qty_to_deliver
		FROM `tabSales Order Item` sii
		INNER JOIN `tabSales Order` si ON sii.parent = si.name
		WHERE sii.docstatus = 1 AND si.docstatus = 1 AND si.status NOT IN ('Completed', 'Closed')
		GROUP BY sii.item_code, IFNULL(sii.production_year, "")
		HAVING SUM(sii.qty - sii.delivered_qty) > 0
	),
	stock_ledger_entry_value AS (
		SELECT item_code, SUM(actual_qty) AS actual_qty, SUM(stock_value_difference) AS stock_value
		FROM `tabStock Ledger Entry`
		WHERE is_cancelled = 0
		GROUP BY item_code
	),
	item_price AS (
		SELECT name, item_code, IFNULL(production_year, "") AS production_year, price_list_rate
		FROM `tabItem Price`
		WHERE selling = 1
			AND price_list IN (
				SELECT value
				FROM `tabSingles`
				WHERE doctype = 'Selling Settings'
					AND field = 'selling_price_list'
			)
	)
	SELECT
		pri.item_code,
		pri.item_name,
		pri.brand,
		pri.production_year,
		pri.qty AS receipt_qty,
		pri.total_cost_amount / pri.qty AS receipt_valuation_rate,
		IF(pri.docstatus = 1, sle_qty.actual_qty, IFNULL(sle_qty.actual_qty, 0) + pri.qty) AS stock_qty,
		IF(pri.docstatus = 1, sle_qty.actual_qty - IFNULL(soi.qty_to_deliver, 0), IFNULL(sle_qty.actual_qty, 0) + pri.qty - IFNULL(soi.qty_to_deliver, 0)) AS available_qty,
		IF(pri.docstatus = 1, sle_value.stock_value,
			IFNULL(sle_value.stock_value, 0) + pri.total_cost_amount) /
			IF(pri.docstatus = 1, sle_value.actual_qty,
			IFNULL(sle_value.actual_qty, 0) + pri.qty) AS stock_valuation_rate,
		ip.price_list_rate AS selling_price,
		ip.name AS price_name
	FROM purchase_receipt_item pri
	LEFT JOIN stock_ledger_entry_qty sle_qty ON pri.item_code = sle_qty.item_code AND pri.production_year <=> sle_qty.production_year
	LEFT JOIN sales_order_item soi ON pri.item_code = soi.item_code AND pri.production_year <=> soi.production_year
	LEFT JOIN stock_ledger_entry_value sle_value ON pri.item_code = sle_value.item_code
	LEFT JOIN item_price ip ON pri.item_code = ip.item_code AND pri.production_year <=> ip.production_year
	INNER JOIN `tabItem` i ON pri.item_code = i.name
	LEFT JOIN `tabTire Size` ts ON i.tire_size = ts.name
	ORDER BY i.brand, ts.sorting_code, i.ply_rating, pri.production_year
	"""

	return frappe.db.sql(sql, values=[purchase_receipt], as_dict=1)

@frappe.whitelist()
def edit_item_price(values, selling_price_list=None):
	values = json.loads(values)
	for row in values:
		plr = frappe.db.get_value("Item Price", row['name'], "price_list_rate")
		if (plr or plr == 0) and plr != row['price']:
			frappe.db.set_value("Item Price", row['name'], "price_list_rate", row['price'])
		if plr is None:
			if not selling_price_list:
				selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
			item_price = frappe.get_doc({
				"doctype": "Item Price",
				"item_code": row['item_code'],
				"item_name": row['item_name'],
				"production_year": row.get('production_year', None),
				"price_list": selling_price_list,
				"price_list_rate": row['price']
			})
			item_price.insert()
