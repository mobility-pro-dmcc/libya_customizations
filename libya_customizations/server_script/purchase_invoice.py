import frappe
from frappe import _
from frappe.utils import flt, getdate
def before_update_after_submit(doc, method):
    purchase_receipt = frappe.db.get_value("Purchase Receipt Item", [["purchase_invoice", "=", doc.name]], "parent")
    if purchase_receipt:
        frappe.db.set_value("Purchase Receipt", purchase_receipt, dict(
            freight_account = doc.freight_account,
            freight_account_currency = doc.freight_account_currency,
            freight_amount = doc.freight_amount or 0,
            freight_exchange_rate = doc.freight_exchange_rate or 0,
            inspection_account = doc.inspection_account,
            inspection_account_currency = doc.inspection_account_currency,
            inspection_amount = doc.inspection_amount or 0,
            inspection_exchange_rate = doc.inspection_exchange_rate or 0,
            clearance_account = doc.clearance_account,
            clearance_amount = doc.clearance_amount or 0,
            transport_account = doc.transport_account,
            transport_amount = doc.transport_amount or 0,
            foreign_bank_charges_account = doc.foreign_bank_charges_account,
            foreign_bank_charges_account_currency = doc.foreign_bank_charges_account_currency,
            foreign_bank_charges_amount = doc.foreign_bank_charges_amount or 0,
            foreign_bank_charges_exchange_rate = doc.foreign_bank_charges_exchange_rate or 0,
            local_bank_charges_account = doc.local_bank_charges_account,
            local_bank_charges_amount = doc.local_bank_charges_amount or 0,
            other_foreign_charges_account = doc.other_foreign_charges_account,
            other_foreign_charges_account_currency = doc.other_foreign_charges_account_currency,
            other_foreign_charges_amount = doc.other_foreign_charges_amount,
            other_foreign_charges_exchange_rate = doc.other_foreign_charges_exchange_rate,
            other_local_charges_account = doc.other_local_charges_account,
            other_local_charges_amount = doc.other_local_charges_amount,
        ))
        pr = frappe.get_doc("Purchase Receipt", purchase_receipt)
        pr.save()

def validate_post_carriage_costs(doc, method):
    if not doc.update_stock:
        if not doc.clearance_account:
            frappe.throw(_("Clearance Account is mandatory"))
        if not doc.clearance_amount:
            frappe.throw(_("Clearance Amount is mandatory"))
        if not doc.transport_account:
            frappe.throw(_("Transport Account is mandatory"))
        if not doc.transport_amount:
            frappe.throw(_("Transport Amount is mandatory"))



@frappe.whitelist()
def update_exchange_rate(invoice_name, new_rate):
    """Popup handler to update exchange rate for a submitted Purchase Invoice."""
    doctype = "Purchase Invoice"
    user_roles = frappe.get_roles(frappe.session.user)
    # --- Step 0: Role check ---
    if "Accounts User" not in user_roles:
        frappe.throw(_("You are not permitted to perform this action"))

    # --- Step 1: Load document ---
    doc = frappe.get_doc(doctype, invoice_name)
    if doc.docstatus != 1:
        frappe.throw(_("Invoice must be submitted first"))

    # --- Step 2: Check Accounts Settings frozen date ---
    acc_settings = frappe.get_single("Accounts Settings")
    frozen_upto = acc_settings.acc_frozen_upto
    if frozen_upto and getdate(doc.posting_date) <= getdate(frozen_upto) and acc_settings.frozen_accounts_modifier not in user_roles:
        frappe.throw(
            _("Cannot update exchange rate. Accounts are frozen up to {0}.")
            .format(frozen_upto)
        )
    # ------------------        
    # edit invoice
    # -------------------
    # --- Step 3: Cancel invoice (make draft) ---
    _toggle_docstatus(doc, 0)

    # --- Step 4: Update exchange rate ---
    doc.reload()
    doc.set("conversion_rate", flt(new_rate))
    doc.save(ignore_permissions=True)
    # --- Step 5: Resubmit invoice ---
    _toggle_docstatus(doc, 1)

    # --- Step 6: Repost Accounting Ledger ---
    ral = frappe.get_doc({
        "doctype": "Repost Accounting Ledger",
        "company": doc.company,
        "delete_cancelled_entries": 1,
        "vouchers": [
            {"voucher_type": doc.doctype, "voucher_no": doc.name}
        ]
    })
    ral.insert(ignore_permissions=True)
    ral.reload()
    ral.submit()

    #------------------------
    # edit receipt
    #------------------------
    if receipt_name := frappe.db.get_value("Purchase Receipt Item", {"purchase_invoice":doc.name}, "parent"):
        receipt = frappe.get_doc("Purchase Receipt", receipt_name)
        old_status = receipt.docstatus
        if old_status == 1:
            _toggle_docstatus(receipt, 0)

        receipt.reload()
        receipt.set("conversion_rate", flt(new_rate))
        receipt.save(ignore_permissions=True)

        if old_status == 1:
            _toggle_docstatus(receipt, 1)
    return {"status": "success", "msg": _("Exchange rate updated and ledger reposted.")}


def _toggle_docstatus(doc, status):
    """Helper to change docstatus of parent and child tables."""
    doctype = doc.doctype
    frappe.db.set_value(doctype, doc.name, "docstatus", status)
    tables = [item for item in doc.as_dict().values() if isinstance(item, list)]
    for row in tables:
        for child in row:
            frappe.db.set_value(child.doctype, child.name, "docstatus", status)


def handle_title_change(doc, method=None):
    """Handle changes to Purchase Invoice title."""
    # Get the previous version of this doc from the DB
    old_doc = doc.get_doc_before_save()
    if not old_doc:
        return

    old_title = old_doc.title
    old_bill_no = old_doc.bill_no
    new_title = doc.title

    # If title didn't change, nothing to do
    if not new_title or new_title == old_title:
        return

    # ---------------------
    # Draft: just bill_no
    # ---------------------
    if doc.docstatus == 0:
        doc.db_set("bill_no", new_title)
        return
    

    # Only handle submitted; ignore cancelled etc.
    if doc.docstatus != 1:
        return

    # ----------------------------------------
    # 1) Check for conflicting Purchase Receipt
    # ----------------------------------------
    pr_conflict = frappe.db.exists(
        "Purchase Receipt",
        {
            "docstatus": 1,
            "title": old_title,
        },
    )
    if pr_conflict:
        # This will rollback the whole save
        frappe.throw(
            _(
                "Cannot change title to '{0}' because a submitted Purchase Receipt "
                "already has this title: {1}"
            ).format(new_title, pr_conflict),
            frappe.ValidationError,
        )

    # ----------------------------------------
    # 2) Update Purchase Invoice fields (in doc)
    # ----------------------------------------
    bill_date = doc.get("bill_date")
    formatted_date = frappe.utils.formatdate(bill_date) if bill_date else None

    doc.db_set("bill_no", new_title)
    remarks = f"Against Supplier Invoice {doc.bill_no}"
    if formatted_date:
        remarks += f" dated {formatted_date}"
    doc.db_set("remarks", remarks)

    # ----------------------------------------
    # 3) Update related Purchase Receipts (via DB)
    # ----------------------------------------
    pr_names = frappe.db.get_list(
        "Purchase Receipt",
        filters={
            "title": old_title,
        },
        pluck="name",
    )

    for pr_name in pr_names:
        frappe.db.set_value(
            "Purchase Receipt",
            pr_name,
            {
                "supplier_delivery_note": new_title,
                "title": new_title,
                "remarks": new_title,
            },
        )
    # ----------------------------------------
    # 4) Repost Accounting Ledger for this invoice
    # ----------------------------------------
    repost = frappe.get_doc(
        {
            "doctype": "Repost Accounting Ledger",
            "company": doc.company,
            "delete_cancelled_entries": 1,
            "vouchers": [
                {
                    "voucher_type": doc.doctype,
                    "voucher_no": doc.name,
                }
            ],
        }
    )
    repost.insert(ignore_permissions=True)
    repost.submit()


def add_item_prices(doc):
    # 1. get all selling price lists once
    price_lists = frappe.db.get_list(
        "Price List",
        {"selling": 1},
        pluck="name",
        ignore_permissions=True
    )

    if not doc.items:
        return

    # 2. collect all production years
    production_years = list({(None if item.production_year == '' else item.production_year) for item in doc.items})

    # 3. get existing item prices once
    existing_prices = frappe.db.get_all(
        "Item Price",
        filters={
            "item_code": ["in", [item.item_code for item in doc.items]],
            "price_list": ["in", price_lists],
            "production_year": ["in", production_years],
        },
        fields=["price_list", "production_year", "item_code"]
    )

    # 4. build fast lookup set
    existing_set = {
        (row.price_list, row.production_year, row.item_code)
        for row in existing_prices
    }
    # 5. create missing item prices
    for item in doc.items:
        for price_list in price_lists:
            key = (price_list, (None if item.production_year == '' else item.production_year), item.item_code)

            if key in existing_set:
                continue
            frappe.get_doc({
                "doctype": "Item Price",
                "item_code": item.item_code,
                "price_list": price_list,
                "price_list_rate": 0,
                "selling": 1,
                "item_name": doc.item_name,
                "brand": doc.brand,
                "item_description": doc.description,
                "production_year": (None if item.production_year == '' else item.production_year)
            }).insert(ignore_permissions=True)
            existing_set.add(key)