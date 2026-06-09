# Copyright (c) 2024, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from libya_customizations.utils import reconcile_payments as reconcile_payments_entries


class ClearingVoucher(Document):
	def before_submit(self):
		self.update_status("Submitted")
	def validate(self):
		self.update_status("Draft")
		if self.base_deducted_amount != self.base_added_amount:
			frappe.msgprint(msg=_(f'Deducted Amount in Company Currency not equal to Added Amount in Company Currency'), title=_('Mismatch'), indicator='red')
			raise frappe.ValidationError
		
	def on_submit(self):
		accounts = []
		accounts.append({
			'account': self.from_account,
			'party_type': self.from_party_type,
			'party': self.from_party,
			'exchange_rate': self.source_exchange_rate,
			'credit_in_account_currency': abs(self.deducted_amount)
		})
		accounts.append({
			'account': self.to_account,
			'party_type': self.to_party_type,
			'party': self.to_party,
			'exchange_rate': self.target_exchange_rate,
			'debit_in_account_currency': abs(self.added_amount)
		})
		journal_entry = frappe.get_doc({
			'doctype': 'Journal Entry',
			'company': self.company,
			'posting_date': self.posting_date,
			'accounts': accounts,
			'voucher_type': 'Journal Entry',
			'cheque_no': self.name,
			'cheque_date': self.posting_date,
			'custom_voucher_type': 'Clearing Voucher',
			'custom_voucher_no': self.name,
			'user_remark': self.remark,
			'multi_currency': 1
		})
		journal_entry.insert(ignore_permissions=True)
		journal_entry.submit()
	
		self.on_update_after_submit()
		self.update_status("Submitted")
		if self.from_party_type == "Customer" or self.to_party_type == "Customer":
			self.reconcile_everything()

	def on_update_after_submit(self):
		doctype = 'Journal Entry'
		affected_field = "remark"
		linked_doc = frappe.db.get_value(doctype, {"custom_voucher_no": self.name}, "name")
		if linked_doc:
			frappe.db.set_value("GL Entry", {"voucher_no": linked_doc}, "remarks", self.remark)
			frappe.db.set_value(doctype, linked_doc, affected_field, self.remark)

	def on_trash(self):
		doctype = 'Journal Entry'
		lst = frappe.db.get_list(doctype, filters={'custom_voucher_no': self.name}, ignore_permissions=True)
		for dn in lst:
			frappe.delete_doc(doctype, dn.name, force=True)

	def update_status(self, status):
		self.set("status", status)
	def on_cancel(self):
		self.update_status("Cancelled")

	def before_cancel(self):
		doctype = 'Journal Entry'
		lst = frappe.db.get_list(doctype, filters={'custom_voucher_no': self.name}, ignore_permissions=True)
		for dn in lst:
			d = frappe.get_doc(doctype, dn.name)
			if d.docstatus == 1:
				d.cancel()
		self.update_status("Cancelled")

	def reconcile_payments(self):
		if 'Customer' in [self.from_party_type, self.to_party_type]:
			company = self.company
			account = frappe.db.get_value("Company", company, "default_receivable_account")
			party_info = []
			party_tab = [('from_party_type', 'from_party', 'from_account'), ('to_party_type', 'to_party', 'to_account')]
			for party_type, party, account in party_tab:
				if self.get(party_type) == 'Customer':
					party_info.append({
						'party': self.get(party),
						'account': self.get(account)
					})

			for customer_info in party_info:
				customer = customer_info['party']
				account = customer_info['account']
				reconcile_payments_entries(
					customer=customer,
					account=account,
					company=company
				)
				

	def reconcile_everything(self):
		self.reconcile_payments()
		frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")