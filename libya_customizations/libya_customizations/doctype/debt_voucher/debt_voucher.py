# Copyright (c) 2024, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DebtVoucher(Document):
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
	def on_cancel(self):
		self.update_status("Cancelled")

	def on_update_after_submit(self):
		doctype = 'Journal Entry'
		affected_field = "remark"
		linked_doc = frappe.db.get_value(doctype, {"custom_voucher_no": self.name}, "name")
		if linked_doc:
			frappe.db.set_value("GL Entry", {"voucher_no": linked_doc}, "remarks", self.remark)
			frappe.db.set_value(doctype, linked_doc, affected_field, self.remark)


	# def reconcile_payments(self):
	# 	for company in frappe.get_all("Company"):
	# 		company = company.name
	# 		account = frappe.db.get_value("Company", company, "default_receivable_account")
	# 		for customer in frappe.get_all("Customer"):
	# 			outstanding_documents = frappe.call('erpnext.accounts.doctype.payment_entry.payment_entry.get_outstanding_reference_documents', args = {'party_type':'Customer', 'party':customer.name, 'party_account':account}) or 0
	# 			flag = False
	# 			if outstanding_documents:
	# 				total = 0
	# 				for i in outstanding_documents:
	# 					if i.outstanding_amount > 0:
	# 						flag = True
	# 						break
	# 			if flag:
	# 				unallocated_amount = frappe.db.get_value("Payment Entry", [["party", "=", customer.name], ["unallocated_amount", ">", 0], ["docstatus", "=", 1]], "sum(unallocated_amount)") or 0
	# 				credit_amount = frappe.db.get_value("Journal Entry Account", [["party", "=", customer.name], ["credit", ">", 0], ["reference_name", "=", None], ["docstatus", "=", 1]], "sum(credit)") or 0
	# 				if unallocated_amount or credit_amount:
	# 					reconciliation = frappe.get_doc({
	# 						"doctype": "Process Payment Reconciliation",
	# 						"party_type": "Customer",
	# 						"party" : customer.name,
	# 						"company": company,
	# 						"receivable_payable_account": account,
	# 						"default_advance_account": account
	# 					}).insert(ignore_permissions=True)
	# 					reconciliation.save(ignore_permissions=True)
	# 					reconciliation.submit(ignore_permissions=True)

	# def reconcile_everything(self):
	# 	self.reconcile_payments()
	# 	frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")

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

	def reconcile_payments(self):
		if self.party_type == 'Customer':
			from libya_customizations.utils import create_customer_reconciliation
			create_customer_reconciliation(
				party=self.party,
				company=self.company,
				account=self.from_or_to_account
			)

	def reconcile_everything(self):
		self.reconcile_payments()
		frappe.call("erpnext.accounts.doctype.process_payment_reconciliation.process_payment_reconciliation.trigger_reconciliation_for_queued_docs")