// Copyright (c) 2026, Ahmed Zaytoon and contributors
// For license information, please see license.txt

class AccountClosingVoucher {
    refresh() {
        this.set_accounts_query(this.frm);	
        this.add_ledger_button(this.frm);
    }

    closing_account() {
        this.set_accounts_query(this.frm);
    }

    set_accounts_query(frm) {
        frm.set_query("account", "accounts_to_close", function() {
                let filters = {
                    report_type: 'Balance Sheet',
                    is_group: 0,
                    account_currency: frm.doc.closing_account_currency
                }
                if (frm.doc.closing_account) {
                    filters.name = ["!=", frm.doc.closing_account]
                }
            return {
                filters
            }
        });
    }

    add_ledger_button(frm) {
        if (frm.doc.docstatus > 0) {
			frm.add_custom_button(
				__("Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: frm.doc.name,
						from_date: frm.doc.posting_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						categorize_by: "",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				"fa fa-table"
			);
		}
    }
}

// frappe.ui.form.on("Account Closing Voucher", new AccountClosingVoucher());
extend_cscript(cur_frm.cscript, new AccountClosingVoucher());
