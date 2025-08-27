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
               
            },{
                'fieldname': 'Tiang',
                'label': 'Tiang',
                'fieldtype': 'Select',
                'options': '\nDengan Tiang\nTanpa Tiang\nTukar Tiang',
                'insert_after': 'check_price'
            }
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
               
            },{
                'fieldname': 'Tiang',
                'label': 'Tiang',
                'fieldtype': 'Select',
                'options': '\nDengan Tiang\nTanpa Tiang\nTukar Tiang',
                'insert_after': 'check_price'
            }
        ],
        'Purchase Order': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'supplier',
                'read_only': 1,
            },
        ],
        'Purchase Order Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ],
        'Purchase Receipt': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'supplier',
                'read_only': 1,
            },
        ],
        'Purchase Receipt Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ],
        'Purchase Invoice': [
            {
                'fieldname': 'current_outstanding',
                'label': 'Current Outstanding',
                'fieldtype': 'Currency',
                'insert_after': 'supplier',
                'read_only': 1,
            },
        ],
        'Purchase Invoice Item': [
            {
                'fieldname': 'check_price',
                'label': 'Check Price',
                'fieldtype': 'Button',
                'insert_after': 'item_code'
               
            },
        ],
        "Stock Entry": [
            {
                'fieldname': 'doc_reference',
                'label': 'Doc Reference',
                'fieldtype': 'Data',
                'insert_after': 'to_warehouse'
            }
        ]
    }

    for doctype, fields in custom_fields.items():
        for field in fields:
            create_custom_field(doctype, field)