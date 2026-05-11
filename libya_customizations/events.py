import frappe
def repost_incorrect_sles():
    stock_closing_date = frappe.db.get_single_value('Stock Settings', 'stock_frozen_upto')
    company = frappe.db.get_default('Company')

    voucher_set = set()

    for diff_filter in ['Qty', 'Value', 'Valuation']:
        result = frappe.call(
            "frappe.desk.query_report.run",
            report_name="Stock Ledger Variance",
            filters={"company": company, "difference_in": diff_filter},
            ignore_prepared_report=True
        )

        for i in result.get("result", []):
            if i.posting_date > stock_closing_date and (
                abs(i.difference_in_qty) > 0
                or abs(i.diff_value_diff) > 0.0009
                or abs(i.valuation_diff) > 0.0009
            ):
                voucher = (i.voucher_type, i.voucher_no)
                if voucher not in voucher_set:
                    voucher_set.add(voucher)
                    repost_entry = frappe.get_doc({
                        'doctype': 'Repost Item Valuation',
                        'based_on': 'Transaction',
                        'posting_date': i.posting_date,
                        'posting_time': i.posting_time,
                        'voucher_type': i.voucher_type,
                        'voucher_no': i.voucher_no
                    })
                    repost_entry.insert()
                    repost_entry.submit()
                    frappe.db.commit()