app_name = "libya_customizations"
app_title = "Libya Customizations"
app_publisher = "Ahmed Zaytoon"
app_description = "for all customizations for libya"
app_email = "citybirdman@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "libya_customizations",
# 		"logo": "/assets/libya_customizations/logo.png",
# 		"title": "Libya Customizations",
# 		"route": "/libya_customizations",
# 		"has_permission": "libya_customizations.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/libya_customizations/css/libya_customizations.css"
app_include_js = "/assets/libya_customizations/js/xlsx.full.min.js"

# include js, css files in header of web template
# web_include_css = "/assets/libya_customizations/css/libya_customizations.css"
# web_include_js = "/assets/libya_customizations/js/libya_customizations.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "libya_customizations/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}
# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Sales Invoice" : "public/sales_invoice.js",
	"Stock Entry" : "public/stock_entry.js",
	"Purchase Invoice": "public/purchase_invoice.js",
	"Account" : "public/account.js",
    "Journal Entry": "public/journal_entry.js",
    "Payment Entry": "public/payment_entry.js"
}

doctype_list_js = {
    "Sales Invoice" : "public/sales_invoice_list.js",
    "Item Price" : "public/item_price_list.js",
    "Purchase Invoice" : "public/purchase_invoice_list.js"
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "libya_customizations/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
jinja = {
	"methods": [
		"libya_customizations.server_script.apis.get_customer_credit_balance_w_so",
        "libya_customizations.server_script.apis.get_customer_credit_balance_wo_so",
		]
# 	"filters": "libya_customizations.utils.jinja_filters"
}
fixtures = [
    {
        "doctype": "Server Script",
        "filters": [["module" , "in" , ("Libya Customizations" )]]
    },
    {
        "doctype": "Client Script",
        "filters": [["module" , "in" , ("Libya Customizations" )]]
    },
    {
        "doctype": "Custom HTML Block"
    },
    {
        "doctype": "Restrict Account View"
    },
    {
        "doctype": "Translation"
    },
    {
        "doctype": "Number Card"
    }
]
# Installation
# ------------

# before_install = "libya_customizations.install.before_install"
after_install = "libya_customizations.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "libya_customizations.uninstall.before_uninstall"
# after_uninstall = "libya_customizations.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "libya_customizations.utils.before_app_install"
# after_app_install = "libya_customizations.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "libya_customizations.utils.before_app_uninstall"
# after_app_uninstall = "libya_customizations.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "libya_customizations.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
    "Item Price": "libya_customizations.overrides.item_price.CustomItemPrice"
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    # "Journal Entry":{
    #     "before_cancel":"libya_customizations.server_script.journal_entry.on_trash"
    # },
    "Item": {
        "after_insert": "libya_customizations.server_script.Item.after_insert_item",
        "on_update": "libya_customizations.server_script.Item.after_update_item"
    },
    "Sales Invoice":{
        "on_submit":[
            "libya_customizations.server_script.sales_invoice.after_submit_amended_sales_invoice",
			"libya_customizations.server_script.sales_invoice.reconcile_payments",
			"libya_customizations.server_script.sales_invoice.reconcile_everything",
            "libya_customizations.server_script.sales_invoice.notify_other_branch_users"
        ],
        "before_cancel":[
			"libya_customizations.server_script.sales_invoice.cancel_linked_payment"
        ],
        "before_submit": [
            "libya_customizations.server_script.sales_invoice.before_submit_sales_invoice",
            "libya_customizations.server_script.sales_invoice.validate_before_submit_sales_invoice",
            "libya_customizations.server_script.sales_invoice.before_submit_sales_invoice2"
        ],

		"on_trash": [
			"libya_customizations.server_script.sales_invoice.delete_linked_payment_log",
			"libya_customizations.server_script.sales_invoice.delete_linked_payment"
		],
        "on_update_after_submit": [
            "libya_customizations.server_script.sales_invoice.after_update_after_submit_sales_invoice",
			"libya_customizations.server_script.sales_invoice.validate_before_submit_sales_invoice",
			"libya_customizations.server_script.sales_invoice.create_payment",
			"libya_customizations.server_script.sales_invoice.reconcile_payments",
			"libya_customizations.server_script.sales_invoice.reconcile_everything",
		]
    },
    "Stock Ledger Entry": {
        "on_update": "libya_customizations.server_script.stock_ledger_entry.update_item_price"
    },
    "Purchase Invoice": {
        "on_submit": "libya_customizations.server_script.purchase_invoice.on_submit",
        "on_update_after_submit": "libya_customizations.server_script.purchase_invoice.on_update_after_submit",
        "on_cancel": "libya_customizations.server_script.purchase_invoice.on_cancel",
        "before_update_after_submit": "libya_customizations.server_script.purchase_invoice.update_status",
        "before_cancel": "libya_customizations.server_script.purchase_invoice.update_status",
        "before_submit": "libya_customizations.server_script.purchase_invoice.update_status",
    }
}

# Scheduled Tasks
# ---------------
# scheduler_events = {
#     "cron": {
#         "0 */8 * * *": [
#             "libya_customizations.server_script.sales_invoice.trigger_reconcile_payments"
#         ]
#     }
# }
# scheduler_events = {
# 	"all": [
# 		"libya_customizations.tasks.all"
# 	],
# 	"daily": [
# 		"libya_customizations.tasks.daily"
# 	],
# 	"hourly": [
# 		"libya_customizations.tasks.hourly"
# 	],
# 	"weekly": [
# 		"libya_customizations.tasks.weekly"
# 	],
# 	"monthly": [
# 		"libya_customizations.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "libya_customizations.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "libya_customizations.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "libya_customizations.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["libya_customizations.utils.before_request"]
# after_request = ["libya_customizations.utils.after_request"]

# Job Events
# ----------
# before_job = ["libya_customizations.utils.before_job"]
# after_job = ["libya_customizations.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"libya_customizations.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }


website_route_rules = [{'from_route': '/libya/<path:app_path>', 'to_route': 'libya'},]
