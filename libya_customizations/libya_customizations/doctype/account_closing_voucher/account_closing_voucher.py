# Copyright (c) 2026, Ahmed Zaytoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.accounts.utils import get_balance_on

__ACTIVE_ACCOUNTS_NUMBER__ = 40

class AccountClosingVoucher(Document):
	def validate(self):
		""" validate accounts to be the following:
			    report_type = 'Balance Sheet'
				is_group = 0
				name != parent.closing_account
				currency = parent.closing_account.currency
		"""
		accounts = [row.account for row in self.accounts_to_close]
		if self.closing_account in accounts:
			frappe.throw("Closing account cannot be in the list of accounts to close")
			return
		accounts_data = frappe.get_all(
			"Account",
			filters={"name": ["in", accounts]},
			fields=["name", "report_type", "is_group", "account_currency"]
		)

		for account in accounts_data:
			self.validate_account(account)

	def validate_account(self, account):
		if account.report_type != "Balance Sheet":
			frappe.throw(f"Account {account.name} is not a balance sheet account")
		if account.is_group:
			frappe.throw(f"Account {account.name} is a group account")
		if account.account_currency != self.closing_account_currency:
			frappe.throw(f"Account {account.name} currency does not match closing account currency")
	def on_submit(self):
		self.create_or_enqueue_closing_entries()

	def create_or_enqueue_closing_entries(self):
		if self.accounts_to_close and len(self.accounts_to_close) > __ACTIVE_ACCOUNTS_NUMBER__:
			frappe.enqueue(self.create_closing_entries, queue="long", timeout=600)
		else:
			self.create_closing_entries()

	def create_closing_entries(self):
		for row in self.accounts_to_close:
			balance = get_balance_on(
				account=row.account,
				company=self.company,
				date=self.posting_date
			)
			if balance != 0:
				self.create_closing_entry(row.account, balance)
	# def create_closing_entry(self, account, balance):
	# 	first_entry = frappe.get_doc({
	# 		"doctype": "GL Entry",
	# 		"account": account,
	# 		"company": self.company,
	# 		"posting_date": self.posting_date,
	# 		"voucher_type": "Account Closing Voucher",
	# 		"voucher_no": self.name,
	# 		"debit": balance if balance < 0 else 0,
	# 		"debit_in_account_currency": balance if balance < 0 else 0,
	# 		"credit": balance if balance > 0 else 0,
	# 		"credit_in_account_currency": balance if balance > 0 else 0,
	# 		"account_currency": frappe.get_value("Account", account, "account_currency"),
	# 		"remarks": self.remarks
	# 	})
	# 	first_entry.insert()
	# 	second_entry = frappe.get_doc({
	# 		"doctype": "GL Entry",
	# 		"account": self.closing_account,
	# 		"company": self.company,
	# 		"posting_date": self.posting_date,
	# 		"voucher_type": "Account Closing Voucher",
	# 		"voucher_no": self.name,
	# 		"debit": balance if balance > 0 else 0,
	# 		"debit_in_account_currency": balance if balance > 0 else 0,
	# 		"credit": balance if balance < 0 else 0,
	# 		"credit_in_account_currency": balance if balance < 0 else 0,
	# 		"account_currency": frappe.get_value("Account", self.closing_account, "account_currency"),
	# 		"remarks": self.remarks
	# 	})
	# 	second_entry.insert()
	
	def create_closing_entry(self, account, balance):
		journal_entry = frappe.get_doc({
			"doctype": "Journal Entry",
			"company": self.company,
			"posting_date": self.posting_date,
			"user_remark": self.remarks,
			"accounts": [
				{
					"account": account,
					"debit": abs(balance) if balance < 0 else 0,
					"debit_in_account_currency": abs(balance) if balance < 0 else 0,
					"credit": abs(balance) if balance > 0 else 0,
					"credit_in_account_currency": abs(balance) if balance > 0 else 0,
					"account_currency": frappe.get_value("Account", account, "account_currency"),
					"reference_type": "Account Closing Voucher",
					"reference_name": self.name,
				},
				{
					"account": self.closing_account,
					"debit": abs(balance) if balance > 0 else 0,
					"debit_in_account_currency": abs(balance) if balance > 0 else 0,
					"credit": abs(balance) if balance < 0 else 0,
					"credit_in_account_currency": abs(balance) if balance < 0 else 0,
					"account_currency": frappe.get_value("Account", self.closing_account, "account_currency"),
					"reference_type": "Account Closing Voucher",
					"reference_name": self.name,
				}
			]
		})
		journal_entry.submit()

	def before_cancel(self):
		self.flags.ignore_links = True

	def on_trash(self):
		entries = set(frappe.get_all("Journal Entry Account", filters={"reference_type": self.doctype, "reference_name": self.name}, fields=["parent"], pluck="parent"))
		for entry in entries:
			jv = frappe.get_doc("Journal Entry", entry)
			jv.flags.ignore_links = True
			if jv.docstatus != 1:
				jv.delete()