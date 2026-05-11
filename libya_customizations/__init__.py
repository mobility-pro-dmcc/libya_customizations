# import frappe
# from libya_customizations.utils import make_xlsx

__version__ = "0.0.1"

# def override_xlsxutils():
#     frappe.utils.xlsxutils.make_xlsx = make_xlsx

try:
    import frappe
    import erpnext
    from erpnext.stock.stock_ledger import update_entries_after
    from libya_customizations.overrides.repost_sl import process_sle

    update_entries_after.process_sle = process_sle
except Exception as e:
    pass