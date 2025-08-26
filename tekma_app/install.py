import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

def update_fields():

    # Define the custom fields to be added
    custom_fields = {
        'Sales Order': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'customer',
                'read_only': 1,
            },
        ],
        'Sales Order Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ],
        'Delivery Note': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'customer',
                'read_only': 1,
            },
        ],
        'Delivery Note Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ],
        'Sales Invoice': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'customer',
                'read_only': 1,
            },
        ],
        'Sales Invoice Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ]
    }

    for doctype, fields in custom_fields.items():
        for field in fields:
            create_custom_field(doctype, field)