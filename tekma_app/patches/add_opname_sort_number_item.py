import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    if not frappe.db.exists("Custom Field", {
        "dt": "Item",
        "fieldname": "opname_sort"
    }):
        field = {
            "fieldname": "opname_sort",
            "label": "Urutan Opname",
            "fieldtype": "Int",
            "default": "0",
            "insert_after": "ratio",
        }

        create_custom_field("Item", field)