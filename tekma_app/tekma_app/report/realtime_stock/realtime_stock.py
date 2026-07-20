# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt


from tekma_app.custom.stock import get_realtime_stock, get_realtime_and_picked_stock

def execute(filters=None):
    
    filters = filters or {}
    picked_stock = filters.get("picked_stock")
    summary = filters.get("summary")
    columns = get_columns()
    if not summary:
        
        append_columns = [
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
        ]
        idx = next(
            i for i, c in enumerate(columns)
            if c.get("fieldname") == "parent_warehouse"
        )
        columns[idx + 1:idx + 1] = append_columns

    data = []
    if picked_stock:
        data = get_realtime_and_picked_stock(filters)
        columns.append({
            "label": "Picked Qty",
            "fieldname": "picked_qty",
            "type": "Int",
            "width": 100
        })
        columns.append({
            "label": "Act. Qty",
            "fieldname": "actual_qty",
            "type": "Int",
            "width": 100
        })
    else:
        data = get_realtime_stock(filters)

    columns.append(
        {
            "label": "UoM",
            "fieldname": "stock_uom",
            "fieldtype": "Data",
            "width": 80,
        }
    )

    return columns, data


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
            "label": "Item Group",
            "fieldname": "item_group",
            "fieldtype": "Data",
            # "options": "Item",
            "width": 100,
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
            "label": "Qty",
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100,
        }
    ]