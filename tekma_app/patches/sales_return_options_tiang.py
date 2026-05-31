import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def execute():
    if not frappe.db.exists("Custom Field", {
        "dt": "Delivery Note",
        "fieldname": "return_tiang"
    }):
        field = {
            "fieldname": "return_tiang",
            "label": "Tiang Dikembalikan?",
            "fieldtype": "Select",
            "default": "",
            "insert_after": "is_return",  # sesuaikan posisi
            "depends_on": "eval:doc.is_return",
            "mandatory_depends_on": "eval:doc.is_return",
            "options": "\nYes\nNo"
        }

        create_custom_field("Delivery Note", field)