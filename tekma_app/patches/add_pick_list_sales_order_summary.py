import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    if not frappe.db.exists("Custom Field", {
        "dt": "Pick List",
        "fieldname": "so_summary_html",
    }):
        fields = {
            "Pick List": [
                {
                    "fieldname": "so_summary_section",
                    "label": "Sales Order Summary",
                    "fieldtype": "Section Break",
                    "collapsible": 1,
                    "insert_after": "prompt_qty",  # sesuaikan posisi
                    "depends_on": "eval:doc.purpose == 'Delivery'"
                },
                {
                    "fieldname": "so_summary_html",
                    "label": "Sales Order Summary",
                    "fieldtype": "HTML",
                    "insert_after": "so_summary_section",  # sesuaikan posisi
                    "hidden": 0,
                }
            ]
        }

        create_custom_fields(fields)