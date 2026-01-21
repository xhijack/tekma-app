app_name = "tekma_app"
app_title = "Tekma App"
app_publisher = "PT Sopwer Teknologi Indonesia"
app_description = "Customize ERPNext for Tekma"
app_email = "ramdani@sopwer.net"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "tekma_app",
# 		"logo": "/assets/tekma_app/logo.png",
# 		"title": "Tekma App",
# 		"route": "/tekma_app",
# 		"has_permission": "tekma_app.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/tekma_app/css/tekma_app.css"
# app_include_js = "/assets/tekma_app/js/tekma_app.js"

# include js, css files in header of web template
# web_include_css = "/assets/tekma_app/css/tekma_app.css"
# web_include_js = "/assets/tekma_app/js/tekma_app.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "tekma_app/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"Sales Order": "public/js/sales_order.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_js = {"Sales Order": "public/js/sales_order.js", 
              "Delivery Note": "public/js/delivery_note.js", 
              "Sales Invoice": "public/js/sales_invoice.js", 
              "Purchase Order": "public/js/purchase_order.js",
            "Purchase Receipt": "public/js/purchase_receipt.js",
            "Purchase Invoice": "public/js/purchase_invoice.js",
            "Stock Entry": "public/js/stock_entry.js"
            }
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "tekma_app/public/icons.svg"

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
# jinja = {
# 	"methods": "tekma_app.utils.jinja_methods",
# 	"filters": "tekma_app.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "tekma_app.install.before_install"
# after_install = "tekma_app.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "tekma_app.uninstall.before_uninstall"
# after_uninstall = "tekma_app.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "tekma_app.utils.before_app_install"
# after_app_install = "tekma_app.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "tekma_app.utils.before_app_uninstall"
# after_app_uninstall = "tekma_app.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "tekma_app.notifications.get_notification_config"

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

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Delivery Note": {
		"on_submit": "tekma_app.utils.delivery_note_on_submit",
        "on_cancel": "tekma_app.utils.delivery_note_on_cancel"
	},
    "Sales Invoice": {
        "on_submit": "tekma_app.utils.sales_invoice_on_submit",
		"on_cancel": "tekma_app.utils.sales_invoice_on_cancel"
	},
    "Stock Entry": {
        "validate": "tekma_app.utils.stock_entry_on_validate",
        "on_submit": "tekma_app.utils.stock_entry_on_submit",
        "on_cancel": "tekma_app.utils.stock_entry_on_cancel",
	},
    "Purchase Invoice": {
        "on_submit": "tekma_app.utils.purchase_invoice_on_submit",
        "on_cancel": "tekma_app.utils.purchase_invoice_on_cancel"
    },
     "Purchase Receipt": {
        "on_submit": "tekma_app.utils.purchase_receipt_on_submit",
        "on_cancel": "tekma_app.utils.purchase_invoice_on_cancel"
    },
    "Sales Order": {
        "before_save": "tekma_app.utils.sales_order_autofill_pembayaran"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"tekma_app.tasks.all"
# 	],
# 	"daily": [
# 		"tekma_app.tasks.daily"
# 	],
# 	"hourly": [
# 		"tekma_app.tasks.hourly"
# 	],
# 	"weekly": [
# 		"tekma_app.tasks.weekly"
# 	],
# 	"monthly": [
# 		"tekma_app.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "tekma_app.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "tekma_app.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "tekma_app.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["tekma_app.utils.before_request"]
after_migrate = ["tekma_app.install.update_fields"]

# Job Events
# ----------
# before_job = ["tekma_app.utils.before_job"]
# after_job = ["tekma_app.utils.after_job"]

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
# 	"tekma_app.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

