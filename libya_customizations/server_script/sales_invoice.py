import frappe
from frappe import _
from frappe import json
from frappe.utils import flt

def unreconcile_linked_payments(doc):
	linked_docs = frappe.call("erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.get_linked_payments_for_doc", company = doc.company, doctype= "Sales Invoice", docname=doc.name)
	selection_map = []
	for elem in linked_docs:
			selection_map = [{
				"company": elem.company,
				"voucher_type": elem.voucher_type,
				"voucher_no": elem.voucher_no,
				"against_voucher_type": "Sales Invoice",
				"against_voucher_no": doc.name,
			}]
			try:
				frappe.call("erpnext.accounts.doctype.unreconcile_payment.unreconcile_payment.create_unreconcile_doc_for_selection", selections=json.dumps(selection_map))
			except:
				continue

def after_submit_sales_invoice_so(doc, method):
	if not (doc.is_return or doc.update_stock or doc.is_opening == "Yes"):
		rows = [{"name": row.so_detail, "qty": row.qty} for row in doc.items]
		for row in rows:
			qty = frappe.db.get_value("Sales Order Item", row["name"], "billed_qty")
			qty = qty if qty else 0
			frappe.db.set_value("Sales Order Item", row["name"], "billed_qty", qty + row["qty"])
		docname = frappe.db.get_value("Sales Order Item", rows[0]['name'], "parent")
		doc = frappe.get_doc("Sales Order", docname)
		flag = True
		for row in doc.items:
			if row.qty != row.billed_qty:
				flag = False
				break
		if flag and doc.per_billed < 100:
			frappe.call("erpnext.selling.doctype.sales_order.sales_order.update_status", status="Closed", name=docname)

def after_submit_sales_invoice_dn(doc, method):
	if not (doc.is_return or doc.update_stock or doc.is_opening == "Yes"):
		rows = [{"name": row.dn_detail, "qty": row.qty} for row in doc.items]

		for row in rows:
			qty = frappe.db.get_value("Delivery Note Item", row["name"], "billed_qty")
			qty = qty if qty else 0
			frappe.db.set_value("Delivery Note Item", row["name"], "billed_qty", qty + row["qty"])
		docname = frappe.db.get_value("Delivery Note Item", rows[0]['name'], "parent")
		total_billed_qty = frappe.db.get_value("Delivery Note Item", {'parent':docname}, 'sum(billed_qty)')
		total_delivered_qty = frappe.db.get_value("Delivery Note Item", {'parent':docname}, 'sum(qty)')
		if total_billed_qty == 0:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', 0)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Not Billed')
		elif total_billed_qty > 0 and total_billed_qty < total_delivered_qty:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', total_billed_qty / total_delivered_qty)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Partly Billed')
		else:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', 100)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Fully Billed')
		
def before_cancel_sales_invoice_so(doc, method):
	if not (doc.is_return or doc.update_stock or doc.is_opening == "Yes"):
		rows = [{"name": row.so_detail, "qty": row.qty} for row in doc.items]

		for row in rows:
			qty = frappe.db.get_value("Sales Order Item", row["name"], "billed_qty")
			qty = qty if qty else 0
			frappe.db.set_value("Sales Order Item", row["name"], "billed_qty", qty - row["qty"])
		docname = frappe.db.get_value("Sales Order Item", rows[0]['name'], "parent")
		doc = frappe.get_doc("Sales Order", docname)
		flag = False
		for row in doc.items:
			if row.qty != row.billed_qty:
				flag = True
				break
		if flag:
			frappe.call("erpnext.selling.doctype.sales_order.sales_order.update_status", status="Draft", name=docname)

def before_cancel_sales_invoice_dn(doc, method):
	if not (doc.is_return or doc.update_stock or doc.is_opening == "Yes"):
		rows = [{"name": row.dn_detail, "qty": row.qty} for row in doc.items]

		for row in rows:
			qty = frappe.db.get_value("Delivery Note Item", row["name"], "billed_qty")
			qty = qty if qty else 0
			frappe.db.set_value("Delivery Note Item", row["name"], "billed_qty", qty - row["qty"])
		docname = frappe.db.get_value("Delivery Note Item", rows[0]['name'], "parent")
		total_billed_qty = frappe.db.get_value("Delivery Note Item", {'parent':docname}, 'sum(billed_qty)')
		total_delivered_qty = frappe.db.get_value("Delivery Note Item", {'parent':docname}, 'sum(qty)')
		if total_billed_qty == 0:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', 0)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Not Billed')
		elif total_billed_qty > 0 and total_billed_qty < total_delivered_qty:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', total_billed_qty / total_delivered_qty)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Partly Billed')
		else:
			frappe.db.set_value('Delivery Note', docname, 'custom_per_billed', 100)
			frappe.db.set_value('Delivery Note', docname, 'billing_status', 'Fully Billed')

			
def get_default_company():
	default_company = frappe.db.get_single_value("Global Defaults", "default_company")
	
	if default_company:
		return default_company
	else:
		# Fallback: get the first company in the list
		company = frappe.get_all("Company", fields=["name"], limit=1)
		return company[0].name if company else None

def before_submit_sales_invoice(doc, method):
	return
	rows = [{"name": row.name, "rate": row.net_rate, "valuation_rate": row.incoming_rate, "item_code": row.item_code, "item_name": row.item_name} for row in doc.items]
	bypass_role = frappe.db.get_value("Company", get_default_company(), "role_bypass_price_list_validation")
	
	if not (frappe.db.get_value("Has Role", [["parent", "=", frappe.session.user], ['role', "in", ["Chief Sales Officer", "Price Exception",bypass_role]]]) or doc.is_return):
		for row in rows:
			if row['rate'] < row['valuation_rate']:
				frappe.throw(_("<b>Net Rate</b> ({0}) of Item <b>{1}</b> is less than <b>Valuation Rate</b>").format('{:0.2f}'.format(row['rate']), row['item_name']))
			elif not frappe.db.get_value("Has Role", [["parent", "=", frappe.session.user], ['role', "in", ["Sales Supervisor", "Chief Sales Officer"]]]):
				for row in rows:
					price_list_rate = frappe.db.get_value("Item Price", [["item_code","=", row['item_code']], ["price_list", "=", doc.selling_price_list]], "price_list_rate")
					if row['rate'] < price_list_rate:
						frappe.throw(_("<b>Net Rate</b> ({0}) of Item <b>{1}</b> is less than <b>Price List Rate</b> ({2})").format('{:0.2f}'.format(row['rate']), row['item_name'], '{:0.2f}'.format(price_list_rate)))

def create_payment(doc, method):
	doc = frappe.get_doc(doc)
	linked_payment_entries = frappe.db.get_list('Payment Entry', filters={'custom_voucher_no': doc.name}, ignore_permissions=True)
	linked_journal_entries = frappe.db.get_list('Journal Entry', filters={'custom_voucher_no': doc.name}, ignore_permissions=True)
	if not linked_payment_entries and not linked_journal_entries:
		unreconcile_linked_payments(doc)
		if doc.custom_payment_value_is_different and doc.custom_payment_value:
			amount = doc.custom_payment_value
		else:
			amount = abs(doc.grand_total)
		if doc.is_paid and not doc.is_return:
			references = []
			references.append({
				'reference_doctype': 'Sales Invoice',
				'reference_name': doc.name,
				'total_amount': doc.grand_total,
				'outstanding_amount': doc.outstanding_amount,
				'allocated_amount': doc.outstanding_amount,
				'due_date': doc.due_date,
				'exchange_rate': doc.conversion_rate
			})      
			payment_entry = frappe.get_doc({
				"doctype": "Payment Entry",
				"payment_type": "Receive",
				"party_type": "Customer",
				"party": doc.customer,
				"company": doc.company,
				"posting_date": doc.posting_date,
				"paid_amount": amount,
				"received_amount": amount,
				"paid_from": doc.debit_to,
				"paid_to": doc.payment_account,
				"target_exchange_rate": doc.conversion_rate,
				"paid_to_account_currency": doc.currency,
				"source_exchange_rate": doc.conversion_rate,
				"paid_from_account_currency": doc.currency,
				"reference_no": doc.name,
				"custom_voucher_type": "Sales Invoice",
				"custom_voucher_no": doc.name,
				"reference_date": doc.posting_date,
				"references": references,
				"custom_remarks": 1,
				'remarks': f'استلام مقابل فاتورة مبيعات نقدية رقم {doc.name}',
				'cannot_be_cancelled': 1
			})
			payment_entry.insert(ignore_permissions=True)
			payment_entry.submit()
		elif doc.is_paid and doc.is_return:
			accounts = []
			accounts.append({
				'account': doc.payment_account,
				'exchange_rate': doc.conversion_rate,
				'credit_in_account_currency': amount
			})
			accounts.append({
				'account': doc.debit_to,
				'party_type': 'Customer',
				'party': doc.customer,
				'exchange_rate': doc.conversion_rate,
				'debit_in_account_currency': amount,
				'reference_type': 'Sales Invoice',
				'reference_name': doc.name
			})
			payment_account_type = frappe.db.get_value('Account', doc.payment_account, 'account_type')
			journal_entry = frappe.get_doc({
				'doctype': 'Journal Entry',
				'company': doc.company,
				'posting_date': doc.posting_date,
				'accounts': accounts,
				'voucher_type': payment_account_type + ' Entry',
				'cheque_no': doc.name,
				'cheque_date': doc.posting_date,
				'custom_voucher_type': 'Sales Invoice',
				'custom_voucher_no': doc.name,
				'user_remark': f'دفع مقابل فاتورة مردودات نقدية رقم {doc.name}',
				'remark': f'دفع مقابل فاتورة مردودات نقدية رقم {doc.name}',
				'multi_currency': 1,
				'cannot_be_cancelled': 1
			}).insert(ignore_permissions=True)
			journal_entry.submit()
		doc.custom_is_payment_value_checked =1
		frappe.db.set_value(doc.doctype, doc.name, "custom_is_payment_value_checked", 1)
		create_write_off(doc, method)

def create_write_off(doc, method):
	if doc.custom_payment_value_is_different and doc.custom_payment_value:
		if abs(doc.grand_total) - doc.custom_payment_value <= 0:
			frappe.throw(_("<b>Payment Value</b> should be less than the grand total, if you need to fully pay the invoice, please uncheck <b>Payment Value Is Differect</b>"))
		debit_account = frappe.db.get_value("Company", doc.company, "write_off_account") if doc.is_return else doc.debit_to
		credit_account = doc.debit_to if doc.is_return else frappe.db.get_value("Company", doc.company, "write_off_account")
		credit_party_type = None if doc.is_return else "Customer"
		credit_party = None if doc.is_return else doc.customer
		debit_party_type = "Customer" if doc.is_return else None
		debit_party = doc.customer if doc.is_return else None
		credit_reference_type = None if doc.is_return else "Sales Invoice"
		credit_reference_name = None if doc.is_return else doc.name
		debit_reference_type = "Sales Invoice" if doc.is_return else None
		debit_reference_name = doc.name if doc.is_return else None
		wo_remark = f'إضافة دين مقابل فاتورة مردودات نقدية رقم {doc.name}' if doc.is_return else f'إعفاء دين مقابل فاتورة مبيعات نقدية رقم {doc.name}'

		journal_entry_obj = {
			"voucher_type": "Write Off Entry",
			"company": doc.company,
			"posting_date": doc.posting_date,
			"doctype": "Journal Entry",
			'custom_voucher_type': 'Sales Invoice',
			'custom_voucher_no': doc.name,
			'multi_currency': 1,
			'user_remark': wo_remark,
			'remark': wo_remark,
			'cannot_be_cancelled': 1,
			"accounts": [{
				"account": debit_account,
				"party_type": credit_party_type,
				"party": credit_party,
				"debit_in_account_currency": 0,
				"debit": 0,
				"credit_in_account_currency": (abs(doc.grand_total) - doc.custom_payment_value),
				"credit": (abs(doc.grand_total) - doc.custom_payment_value),
				"reference_type": credit_reference_type,
				"reference_name": credit_reference_name
			}, {
				"account": credit_account,
				"party_type": debit_party_type,
				"party": debit_party,
				"debit_in_account_currency": (abs(doc.grand_total) - doc.custom_payment_value),
				"debit": (abs(doc.grand_total) - doc.custom_payment_value),
				"credit_in_account_currency": 0,
				"credit": 0,
				"reference_type": debit_reference_type,
				"reference_name": debit_reference_name
			}]
		}
		journal_entry = frappe.get_doc(journal_entry_obj).insert(ignore_permissions=True)
		journal_entry.submit()

def reconcile_payments(doc, method):
    # 1. Check if we are already reconciling to break the loop
    if frappe.flags.in_payment_reconciliation:
        return

    company = doc.company
    account = doc.debit_to
    customer = doc.customer

    outstanding_documents = frappe.call('erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents', args = {'party_type':'Customer', 'party':customer, 'party_account':account}) or []
    
    flag = False
    if outstanding_documents:
        for i in outstanding_documents:
            if flt(i.get('outstanding_amount')) > 0:
                flag = True
                break

    if flag:
        unallocated_amount = flt(frappe.db.get_value("Payment Entry", [["party", "=", customer], ["unallocated_amount", ">", 0], ["docstatus", "=", 1]], "sum(unallocated_amount)"))
        credit_amount = flt(frappe.db.get_value("Journal Entry Account", [["party", "=", customer], ["credit", ">", 0], ["reference_name", "=", None], ["docstatus", "=", 1]], "sum(credit)"))
        cn_amount = flt(frappe.db.get_value("Sales Invoice", [["customer", "=", customer], ["outstanding_amount", "<", 0], ["is_return", "=", 1], ["docstatus", "=", 1]], "sum(outstanding_amount)"))

        if unallocated_amount or credit_amount or cn_amount:
            frappe.flags.in_payment_reconciliation = True
            
            try:
                reconciliation = frappe.get_doc({
                    "doctype": "Process Payment Reconciliation",
                    "party_type": "Customer",
                    "party" : customer,
                    "company": company,
                    "receivable_payable_account": account,
                    "default_advance_account": account
                }).insert(ignore_permissions=True)
                
                reconciliation.submit()
            except Exception as e:
                frappe.log_error(title="Auto-Reconciliation Error", message=frappe.get_traceback())
            finally:
                frappe.flags.in_payment_reconciliation = False

def reconcile_everything(doc, method):
	frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")

def trigger_reconcile_everything():
	frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")

def cancel_linked_payment(doc, method):
	if doc.is_paid:
		doctypes = ['Payment Entry', 'Journal Entry']
		for doctype in doctypes:
			entries = frappe.db.get_list(doctype, filters={'custom_voucher_no': doc.name}, ignore_permissions=True)
			for entry in entries:
				e = frappe.get_doc(doctype, entry.name)
				if e.docstatus == 1:
					e.cancel()

def delete_linked_payment(doc, method):
	if doc.is_paid:
		doctypes = ['Payment Entry', 'Journal Entry']
		for doctype in doctypes:
			entries = frappe.db.get_list(doctype, filters={'custom_voucher_no': doc.name}, ignore_permissions=True)
			for entry in entries:
				frappe.delete_doc(doctype, entry.name, force=True)

def delete_linked_payment_log(doc, method):
	ref_logs = frappe.db.get_list('Process Payment Reconciliation Log Allocations', filters={'reference_type': 'Sales Invoice', 'reference_name':doc.name}, pluck='parent', ignore_permissions=True)
	inv_logs = frappe.db.get_list('Process Payment Reconciliation Log Allocations', filters={'invoice_type': 'Sales Invoice', 'invoice_number':doc.name}, pluck='parent', ignore_permissions=True)
	logs = list(set(ref_logs + inv_logs))
	for log in logs:
		frappe.delete_doc('Process Payment Reconciliation Log', log, force=True)
