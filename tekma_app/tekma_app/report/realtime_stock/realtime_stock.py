# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt


from tekma_app.custom.stock import get_realtime_stock

def execute(filters=None):
    
    filters = filters or {}

    return get_columns(), get_realtime_stock(filters or {})


def get_columns():
    return [
        {
            "label": "Item Code",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 140,
        },
        {
            "label": "Item Name",
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 250,
        },
        {
            "label": "Item Disabled",
            "fieldname": "disabled_item",
            "fieldtype": "Check",
            "width": 50,
        },
        {
            "label": "Warehouse",
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180,
        },
        {
            "label": "Parent Warehouse",
            "fieldname": "parent_warehouse",
            "fieldtype": "Link",
            "options": "Warehouse",
            "width": 180,
        },
        {
            "label": "Batch No",
            "fieldname": "batch_no",
            "fieldtype": "Link",
            "options": "Batch",
            "width": 250,
        },
        {
            "label": "Batch Disabled",
            "fieldname": "disabled_batch",
            "fieldtype": "Check",
            "width": 50,
        },
        {
            "label": "Manufacturing Date",
            "fieldname": "manufacturing_date",
            "fieldtype": "Date",
            "width": 120,
        },
        {
            "label": "Qty",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "UoM",
            "fieldname": "stock_uom",
            "fieldtype": "Data",
            "width": 80,
        },
    ]