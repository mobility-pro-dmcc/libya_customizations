import frappe
from frappe.utils import cint, flt, now
from erpnext.stock.stock_ledger import (
    get_inventory_dimensions,
    is_internal_transfer,
    get_incoming_rate_for_inter_company_transfer,
    get_stock_value_difference,
)
from libya_customizations.server_script.stock_ledger_entry import update_item_price
import json

def process_sle(self, sle):
    # frappe.error_log("Custom process_sle called")
    # previous sle data for this warehouse
    self.wh_data = self.data[sle.warehouse]

    self.validate_previous_sle_qty(sle)
    self.affected_transactions.add((sle.voucher_type, sle.voucher_no))

    if (sle.serial_no and not self.via_landed_cost_voucher) or not cint(self.allow_negative_stock):
        # validate negative stock for serialized items, fifo valuation
        # or when negative stock is not allowed for moving average
        if not self.validate_negative_stock(sle):
            self.wh_data.qty_after_transaction += flt(sle.actual_qty)
            return

    # Get dynamic incoming/outgoing rate
    if not self.args.get("sle_id"):
        self.get_dynamic_incoming_outgoing_rate(sle)

    if (
        sle.voucher_type == "Stock Reconciliation"
        and (sle.batch_no or sle.serial_no or sle.serial_and_batch_bundle)
        and sle.voucher_detail_no
        and not self.args.get("sle_id")
        and sle.is_cancelled == 0
    ):
        self.reset_actual_qty_for_stock_reco(sle)

    if (
        sle.voucher_type in ["Purchase Receipt", "Purchase Invoice"]
        and sle.voucher_detail_no
        and sle.actual_qty < 0
        and is_internal_transfer(sle)
    ):
        sle.outgoing_rate = get_incoming_rate_for_inter_company_transfer(sle)

    dimensions = get_inventory_dimensions()
    has_dimensions = False
    if dimensions:
        for dimension in dimensions:
            if sle.get(dimension.get("fieldname")):
                has_dimensions = True

    if sle.serial_and_batch_bundle:
        self.calculate_valuation_for_serial_batch_bundle(sle)
    elif sle.serial_no and not self.args.get("sle_id"):
        # Only run in reposting
        self.get_serialized_values(sle)
        self.wh_data.qty_after_transaction += flt(sle.actual_qty)
        if sle.voucher_type == "Stock Reconciliation" and not sle.batch_no:
            self.wh_data.qty_after_transaction = sle.qty_after_transaction

        self.wh_data.stock_value = flt(self.wh_data.qty_after_transaction) * flt(
            self.wh_data.valuation_rate
        )
    elif (
        sle.batch_no
        and frappe.db.get_value("Batch", sle.batch_no, "use_batchwise_valuation", cache=True)
        and not self.args.get("sle_id")
    ):
        # Only run in reposting
        self.update_batched_values(sle)
    else:
        if (
            sle.voucher_type == "Stock Reconciliation"
            and not sle.batch_no
            and not sle.has_batch_no
            and not has_dimensions
        ):
            # assert
            self.wh_data.valuation_rate = sle.valuation_rate
            self.wh_data.qty_after_transaction = sle.qty_after_transaction
            self.wh_data.stock_value = flt(self.wh_data.qty_after_transaction) * flt(
                self.wh_data.valuation_rate
            )
            if self.valuation_method != "Moving Average":
                self.wh_data.stock_queue = [
                    [self.wh_data.qty_after_transaction, self.wh_data.valuation_rate]
                ]
        else:
            if self.valuation_method == "Moving Average":
                self.get_moving_average_values(sle)
                self.wh_data.qty_after_transaction += flt(sle.actual_qty)
                self.wh_data.stock_value = flt(self.wh_data.qty_after_transaction) * flt(
                    self.wh_data.valuation_rate
                )

                if (
                    sle.actual_qty < 0
                    and flt(self.wh_data.qty_after_transaction, self.flt_precision) != 0
                ):
                    self.wh_data.valuation_rate = flt(
                        self.wh_data.stock_value, self.currency_precision
                    ) / flt(self.wh_data.qty_after_transaction, self.flt_precision)

            else:
                self.update_queue_values(sle)

    # rounding as per precision
    self.wh_data.stock_value = flt(self.wh_data.stock_value, self.currency_precision)
    if not self.wh_data.qty_after_transaction:
        self.wh_data.stock_value = 0.0

    stock_value_difference = self.wh_data.stock_value - self.wh_data.prev_stock_value
    self.wh_data.prev_stock_value = self.wh_data.stock_value

    # update current sle
    sle.qty_after_transaction = flt(self.wh_data.qty_after_transaction, self.flt_precision)
    sle.valuation_rate = self.wh_data.valuation_rate
    sle.stock_value = self.wh_data.stock_value
    sle.stock_queue = json.dumps(self.wh_data.stock_queue)

    if not sle.is_adjustment_entry:
        sle.stock_value_difference = stock_value_difference
    elif sle.is_adjustment_entry and not self.args.get("sle_id"):
        sle.stock_value_difference = (
            get_stock_value_difference(
                sle.item_code, sle.warehouse, sle.posting_date, sle.posting_time, sle.voucher_no
            )
            * -1
        )
    sle.doctype = "Stock Ledger Entry"
    sle.modified = now()
    sle_doc = frappe.get_doc(sle)
    sle_doc.db_update()
    
    update_item_price(sle_doc)


    if not self.args.get("sle_id") or (
        sle.serial_and_batch_bundle and sle.auto_created_serial_and_batch_bundle
    ):
        self.update_outgoing_rate_on_transaction(sle)