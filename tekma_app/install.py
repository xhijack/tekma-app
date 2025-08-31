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
                "fieldname": "doc_reference",
                "label": "Doc Reference",
                "fieldtype": "Data",
                "insert_after": "bom_no"  # <— taruh persis setelah BOM Info
            },
            {
                "fieldname": "pic",
                "label": "PIC",
                "fieldtype": "Link",
                "options": "Employee",
                "insert_after": "doc_reference",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "asisten",  # (boleh pakai 'Asisten' kalau memang sudah terlanjur dibuat begitu)
                "label": "Asisten",
                "fieldtype": "Link",
                "options": "Employee",
                "insert_after": "pic",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "jenis_paket",
                "label": "Jenis Paket",
                "fieldtype": "Select",
                "options": "Super\nS Mix\nII Mix\nBrows",
                "insert_after": "asisten",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'

            },
            {
                "fieldname": "kode_bak",
                "label": "Kode Bak",
                "fieldtype": "Select",
                "options": "A\nB\nC\nD\nE\nF\nG\nH\nI\nJ\nK\nL\nM\nN\nBLD",
                "insert_after": "jenis_paket",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'

            },
            {
                "fieldname": "durasi_keseluruhan",
                "label": "Durasi Keseluruhan",
                "fieldtype": "Int",
                "insert_after": "kode_bak",
                "default": 1,
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "durasi",
                "label": "Durasi",
                "fieldtype": "Int",
                "default": 1,
                "insert_after": "durasi_keseluruhan",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "kondisi_bahan",
                "label": "Kondisi Bahan",
                "fieldtype": "Select",
                "options": "Normal\nTemuan",
                "insert_after": "durasi",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "kondisi_mesin",
                "label": "Kondisi Mesin",
                "fieldtype": "Select",
                "options": "Normal\nError",
                "insert_after": "kondisi_bahan",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                "fieldname": "ganti_pisau",
                "label": "Ganti Pisau",
                "fieldtype": "Select",
                "options": "Ya\nTidak",
                "insert_after": "kondisi_mesin",
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"'
            },
            {
                'fieldname': 'prod_reference',
                'label': 'Prod Reference',
                'fieldtype': 'Link',
                'options': 'Stock Entry',
                "depends_on": 'eval: doc.stock_entry_type=="Flaker" || doc.stock_entry_type=="Mincer" || doc.stock_entry_type=="Mixer"',
                "insert_after": "stock_entry_type"
            }
        ],
        'Item' : [    
            {
                'fieldname': 'ratio',
                'label': 'Ratio',
                'fieldtype': 'Float',
                'insert_after': 'stock_uom',
                'default': 0,  
            }
        ]
    }

    for doctype, fields in custom_fields.items():
        for field in fields:
            create_custom_field(doctype, field)