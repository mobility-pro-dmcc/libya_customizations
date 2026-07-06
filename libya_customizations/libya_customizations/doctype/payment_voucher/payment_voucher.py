# Copyright (c) 2024, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from frappe import _
from libya_customizations.utils import reconcile_payments as reconcile_payments_entries
from libya_customizations.utils import unreconcile_payments


class PaymentVoucher(Document):
	def validate(self):
		self.update_status("Draft")

		if flt(self.base_paid_amount, self.precision("base_paid_amount")) != flt(self.base_received_amount, self.precision("base_received_amount")):
			frappe.msgprint(msg=_(f'Paid Amount in Company Currency not equal to Received Amount in Company Currency'), title=_('Mismatch'), indicator='red')
			raise frappe.ValidationError
		
	def before_submit(self):
		self.update_status("Submitted")
		
	def on_submit(self):
		if self.payment_to == "Supplier":
			payment_entry = frappe.get_doc({
				"doctype": "Payment Entry",
				"payment_type": "Pay",
				"party_type": "Supplier",
				"party": self.party,
				"company": self.company,
				"posting_date": self.posting_date,
				"paid_amount": abs(self.paid_amount),
				"received_amount": abs(self.received_amount),
				"paid_from": self.paid_from,
				"paid_to": self.paid_to,
				"target_exchange_rate": self.target_exchange_rate,
				"paid_to_account_currency": self.paid_to_account_currency,
				"source_exchange_rate": self.source_exchange_rate,
				"paid_from_account_currency": self.paid_from_account_currency,
				"reference_no": self.name,
				"custom_voucher_type": "Payment Voucher",
				"custom_voucher_no": self.name,
				"reference_date": self.posting_date,
				"custom_remarks": 1,
				"remarks": self.remark
			})
			payment_entry.insert(ignore_permissions=True)
			payment_entry.submit()
		else:
			accounts = []
			accounts.append({
				'account': self.paid_from,
				'exchange_rate': self.source_exchange_rate,
				'credit_in_account_currency': abs(self.paid_amount)
			})
			accounts.append({
				'account': self.paid_to,
				'party_type': self.party_type,
				'party': self.party,
				'exchange_rate': self.target_exchange_rate,
				'debit_in_account_currency': abs(self.received_amount)
			})
			journal_entry = frappe.get_doc({
				'doctype': 'Journal Entry',
				'company': self.company,
				'posting_date': self.posting_date,
				'accounts': accounts,
				'voucher_type': self.paid_from_account_type + ' Entry',
				'cheque_no': self.name,
				'cheque_date': self.posting_date,
				'custom_voucher_type': 'Payment Voucher',
				'custom_voucher_no': self.name,
				'remark': self.remark,
				'multi_currency': 1
			}).insert(ignore_permissions=True)
			journal_entry.submit()
		
		self.on_update_after_submit()
		self.update_status("Submitted")
		if self.payment_to == "Customer":
			self.reconcile_everything()

	def update_status(self, status):
		self.set("status", status)


	def on_update_after_submit(self):
		doctype = 'Journal Entry'
		affected_field = "remark"
		if self.payment_to == "Supplier":
			doctype = "Payment Entry"
			affected_field = "remarks"
		linked_doc = frappe.db.get_value(doctype, {"custom_voucher_no": self.name}, "name")
		if linked_doc:
			frappe.db.set_value("GL Entry", {"voucher_no": linked_doc}, "remarks", self.remark)
			frappe.db.set_value(doctype, linked_doc, affected_field, self.remark)


	
	def on_trash(self):
		doctype = 'Journal Entry'
		if self.payment_to == "Supplier":
			doctype = "Payment Entry"
		lst = frappe.db.get_list(doctype, filters={'custom_voucher_no': self.name}, ignore_permissions=True)
		for dn in lst:
			frappe.delete_doc(doctype, dn.name, force=True)

	def before_cancel(self):
		unreconcile_payments(self)
		doctype = 'Journal Entry'
		if self.payment_to == "Supplier":
			doctype = "Payment Entry"
		lst = frappe.db.get_list(doctype, filters={'custom_voucher_no': self.name}, ignore_permissions=True)
		for dn in lst:
			d = frappe.get_doc(doctype, dn.name)
			if d.docstatus == 1:
				d.cancel()
		self.update_status("Cancelled")

	def reconcile_payments(self):
		if self.party_type == 'Customer':
			reconcile_payments_entries(self.company, self.paid_to, self.party)

	def reconcile_everything(self):
		self.reconcile_payments()
		frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")