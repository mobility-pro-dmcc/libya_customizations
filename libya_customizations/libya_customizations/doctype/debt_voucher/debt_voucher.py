# Copyright (c) 2024, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from libya_customizations.utils import reconcile_payments as reconcile_payments_entries


class DebtVoucher(Document):
	def validate(self):
		self.update_status("Draft")

	def before_submit(self):
		self.update_status("Submitted")
		
	def on_submit(self):	
		if self.type == 'Add':
			accounts_add = []
			debt_account = frappe.db.get_value("Company", self.company, "write_up_account")
			if not debt_account:
				frappe.throw(_("Write Up Account is not set in Company Master"))
			accounts_add.append({
				'account': debt_account,
				'exchange_rate': 1,
				'credit_in_account_currency': abs(self.amount)
			})
			accounts_add.append({
				'account': self.from_or_to_account,
				'party_type': self.party_type,
				'party': self.party,
				'exchange_rate': self.exchange_rate,
				'debit_in_account_currency': abs(self.amount),
			})
			journal_entry = frappe.get_doc({
				'doctype': 'Journal Entry',
				'company': self.company,
				'posting_date': self.posting_date,
				'accounts': accounts_add,
				'voucher_type': 'Write Off Entry',
				'cheque_no': self.name,
				'cheque_date': self.posting_date,
				'custom_voucher_type': 'Debt Voucher',
				'custom_voucher_no': self.name,
				'user_remark': self.remark,
				'multi_currency': 1
			})
			journal_entry.insert(ignore_permissions=True)
			journal_entry.submit()

		elif self.type == 'Deduct':
			debt_account = frappe.db.get_value("Company", self.company, "write_off_account")
			if not debt_account:
				frappe.throw(_("Write Off Account is not set in Company Master"))
			accounts_deduct = []
			accounts_deduct.append({
				'account': self.from_or_to_account,
				'party_type': self.party_type,
				'party': self.party,
				'exchange_rate': self.exchange_rate,
				'credit_in_account_currency': abs(self.amount)
			})
			accounts_deduct.append({
				'account': debt_account,
				'exchange_rate': 1,
				'debit_in_account_currency': abs(self.base_amount)
			})
			journal_entry = frappe.get_doc({
				'doctype': 'Journal Entry',
				'company': self.company,
				'posting_date': self.posting_date,
				'accounts': accounts_deduct,
				'voucher_type': 'Write Off Entry',
				'cheque_no': self.name,
				'cheque_date': self.posting_date,
				'custom_voucher_type': 'Debt Voucher',
				'custom_voucher_no': self.name,
				'user_remark': self.remark,
				'multi_currency': 1
			})
			journal_entry.insert(ignore_permissions=True)
			journal_entry.submit()
		
		self.on_update_after_submit()
		self.update_status("Submitted")
		if self.from_or_to == "Customer":
			self.reconcile_everything()

	def update_status(self, status):
		self.set("status", status)


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

	def before_cancel(self):
		doctype = 'Journal Entry'
		lst = frappe.db.get_list(doctype, filters={'custom_voucher_no': self.name}, ignore_permissions=True)
		for dn in lst:
			d = frappe.get_doc(doctype, dn.name)
			if d.docstatus == 1:
				d.cancel()
		self.update_status("Cancelled")

	def reconcile_payments(self):
		if self.party_type == 'Customer':
			reconcile_payments_entries(self.company, self.from_or_to_account, self.party)

	def reconcile_everything(self):
		self.reconcile_payments()
		frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")