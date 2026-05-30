import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    fields = {
        "Stock Entry": [
            {
                "fieldname": "delivery_note_id",
                "label": "Delivery Note ID",
                "fieldtype": "Link",
                "options": "Delivery Note",
                "insert_after": "bom_no"  # <— taruh persis setelah BOM Info
            },
            {
                "fieldname": "doc_reference",
                "hidden": 1,
                "readonly": 1
            }
        ]
    }
    
    create_custom_fields(fields, update=True)
    se = frappe.get_all(
        "Stock Entry",
        fields=["name", "doc_reference"]
    )

    for d in se:
        if d.doc_reference:
            frappe.db.set_value(
                "Stock Entry",
                d.name,
                "delivery_note_id",
                d.doc_reference,
                update_modified=False
            )

    frappe.reload_doc("Core", "Stock Entry", force=True)

    