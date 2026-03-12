app_name = "std_manufacturing"
app_title = "Std Manufacturing"
app_publisher = "QCS"
app_description = "App for std manufacturing"
app_email = "info@quarkcs.com"
app_license = "mit"

required_apps = ["erpnext"]

after_install = "std_manufacturing.setup.setup_custom_fields"
after_migrate = "std_manufacturing.setup.setup_custom_fields"

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "std_manufacturing",
# 		"logo": "/assets/std_manufacturing/logo.png",
# 		"title": "Std Manufacturing",
# 		"route": "/std_manufacturing",
# 		"has_permission": "std_manufacturing.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/std_manufacturing/css/std_manufacturing.css"
# app_include_js = "/assets/std_manufacturing/js/std_manufacturing.js"

# include js, css files in header of web template
# web_include_css = "/assets/std_manufacturing/css/std_manufacturing.css"
# web_include_js = "/assets/std_manufacturing/js/std_manufacturing.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "std_manufacturing/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "std_manufacturing/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "std_manufacturing.utils.jinja_methods",
# 	"filters": "std_manufacturing.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "std_manufacturing.install.before_install"
# after_install = "std_manufacturing.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "std_manufacturing.uninstall.before_uninstall"
# after_uninstall = "std_manufacturing.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "std_manufacturing.utils.before_app_install"
# after_app_install = "std_manufacturing.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "std_manufacturing.utils.before_app_uninstall"
# after_app_uninstall = "std_manufacturing.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "std_manufacturing.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Purchase Receipt": {
		"before_submit": "std_manufacturing.api.standard_cost.enforce_standard_rate_on_receipt"
	},
	"Stock Entry": {
		"before_submit": "std_manufacturing.api.standard_cost.enforce_standard_rate_on_entry"
	},
	"Purchase Invoice": {
		"on_submit": "std_manufacturing.api.standard_cost.check_freight_invoice"
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"std_manufacturing.tasks.all"
# 	],
# 	"daily": [
# 		"std_manufacturing.tasks.daily"
# 	],
# 	"hourly": [
# 		"std_manufacturing.tasks.hourly"
# 	],
# 	"weekly": [
# 		"std_manufacturing.tasks.weekly"
# 	],
# 	"monthly": [
# 		"std_manufacturing.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "std_manufacturing.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "std_manufacturing.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "std_manufacturing.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "std_manufacturing.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["std_manufacturing.utils.before_request"]
# after_request = ["std_manufacturing.utils.after_request"]

# Job Events
# ----------
# before_job = ["std_manufacturing.utils.before_job"]
# after_job = ["std_manufacturing.utils.after_job"]

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
# 	"std_manufacturing.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

