import frappe
import json
from frappe import _
from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
from libya_customizations.server_script.sales_order import get_customer_info

class CustomSalesOrder(SalesOrder):
    def update_status(self, *args, **kwargs):
        # Call the original update_status method from the parent class
        # old_status = self.status
        super().update_status(*args, **kwargs)
        # frappe.throw(self.status)
        if self.status not in ["Closed", "Completed"]:
            self.validate_before_submit_sales_order()

    def validate_before_submit_sales_order(self):
        payment_terms_template = frappe.db.get_value('Customer', self.customer, 'payment_terms')
        if payment_terms_template:
            bypass_overdue_check = frappe.db.get_value('Customer', self.customer, 'bypass_overdue_check')
            user_has_cso = frappe.db.get_value("Has Role", [["parent", "=", frappe.session.user], ['role', "=", "Chief Sales Officer"]])
            credit_days = frappe.db.get_value('Payment Terms Template Detail', {'parent': payment_terms_template}, 'credit_days')
            outstanding = frappe.db.get_value('Sales Invoice', {'docstatus': 1, 'customer': self.customer, 'posting_date': ['<', frappe.utils.add_days(frappe.utils.nowdate(), - credit_days)]}, 'sum(outstanding_amount)')
            outstanding = outstanding if outstanding else 0

            if outstanding > 0 and not (bypass_overdue_check or user_has_cso):
                frappe.msgprint(msg=_("There are overdue outstandings valued at {0} against the Customer").format('{:0,.2f}'.format(outstanding)), title=_('Error'), indicator='red')
                raise frappe.ValidationError
            elif outstanding > 0 and (bypass_overdue_check or user_has_cso):
                frappe.msgprint(msg=_("There are overdue outstandings valued at {0} against the Customer").format('{:0,.2f}'.format(outstanding)), title=_('Warning'), indicator='orange')
        else:
            frappe.msgprint(msg=_(f"There is no payment terms assigned to Customer in Customer Master"), title=_('Error'), indicator='red')
            raise frappe.ValidationError
        
    @frappe.whitelist()
    def get_customer_metrics(self):
        """Fetches metrics from Redis cache first; falls back to DB only if cache is expired."""
        if not self.customer:
            return {}

        # 1. Define a unique cache key for this specific customer
        cache_key = f"customer_metrics:{self.customer}"
        
        # 2. Try to get the cached data from Redis
        cached_data = frappe.cache().get_value(cache_key)
        
        if cached_data:
            # Cache hit: parse the JSON string back into a Python dict
            return json.loads(cached_data)
            
        # 3. Cache miss: execute your database/API logic
        res = get_customer_info(customer=self.customer)
        metrics = {}
        
        if res and isinstance(res, list) and len(res) > 0:
            metrics = res[0]
            
            # 4. Save to Redis cache and set an expiration time (e.g., 300 seconds / 5 minutes)
            # This ensures the data stays fresh but relieves database pressure completely.
            frappe.cache().set_value(cache_key, json.dumps(metrics), expires_in_sec=300)
            
        return metrics

    # ----------------------------------------------------
    # Properties remain completely unchanged and clean
    # ----------------------------------------------------

    @property
    def customer_balance(self):
        return self.get_customer_metrics().get("customer_balance", 0.0)

    @property
    def customer_actual_overdues(self):
        return self.get_customer_metrics().get("customer_actual_overdues", 0.0)

    @property
    def customer_potential_overdues(self):
        return self.get_customer_metrics().get("customer_potential_overdues", 0.0)

    @property
    def customer_credit_limit(self):
        return self.get_customer_metrics().get("customer_credit_limit", 0.0)

    @property
    def unbilled_sales_orders(self):
        return self.get_customer_metrics().get("unbilled_sales_orders", 0.0)

    @property
    def customer_index(self):
        return self.get_customer_metrics().get("customer_index", "")