import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    if not frappe.db.exists("Custom Field", {
        "dt": "Stock Entry",
        "fieldname": "is_open"
    }):
        field = {
            "fieldname": "is_open",
            "label": "Is Open",
            "fieldtype": "Check",
            "default": "0",
            "insert_after": "set_posting_time",  # sesuaikan posisi
            "allow_on_submit": 1,
            "hidden": 1,
            "default": 1
        }

        create_custom_field("Stock Entry", field)