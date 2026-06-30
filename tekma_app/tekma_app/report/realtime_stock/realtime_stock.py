# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    filters = filters or {}

    columns = [
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
            "width": 140,
        },
        {
            "label": "Manufacturing Date",
            "fieldname": "manufacturing_date",
            "fieldtype": "Date",
            "width": 110,
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
            "width": 100,
        }
    ]

    return columns, get_data(filters)


def get_warehouses(warehouse):
    if not warehouse:
        return []

    is_group = frappe.db.get_value("Warehouse", warehouse, "is_group")

    if not is_group:
        return [warehouse]

    lft, rgt = frappe.db.get_value(
        "Warehouse",
        warehouse,
        ["lft", "rgt"],
    )

    return frappe.get_all(
        "Warehouse",
        filters={
            "lft": [">=", lft],
            "rgt": ["<=", rgt],
        },
        pluck="name",
        order_by="lft",
    )


def get_item_group_condition(item_group, params):
    if not item_group:
        return ""

    lft, rgt = frappe.db.get_value(
        "Item Group",
        item_group,
        ["lft", "rgt"],
    )

    params["ig_lft"] = lft
    params["ig_rgt"] = rgt

    return """
        AND EXISTS (
            SELECT 1
            FROM `tabItem Group` ig
            WHERE ig.name = i.item_group
              AND ig.lft >= %(ig_lft)s
              AND ig.rgt <= %(ig_rgt)s
        )
    """


def get_data(filters):

    params = {}

    conditions_batch = [
        "i.is_stock_item = 1",
        "i.has_batch_no = 1",
        "sle.is_cancelled = 0",
    ]

    conditions_non_batch = [
        "i.is_stock_item = 1",
        "i.has_batch_no = 0",
    ]

    warehouse = filters.get("warehouse")

    if warehouse:
        warehouses = get_warehouses(warehouse)

        params["warehouses"] = tuple(warehouses)

        conditions_batch.append(
            "sle.warehouse IN %(warehouses)s"
        )

        conditions_non_batch.append(
            "bin.warehouse IN %(warehouses)s"
        )

    item_group_condition = get_item_group_condition(
        filters.get("item_group"),
        params,
    )

    query = f"""
    SELECT
        sle.item_code,
        i.item_name,
        sle.warehouse,
        w.parent_warehouse AS parent_warehouse,
        sbe.batch_no,
        b.manufacturing_date,
        SUM(sbe.qty) AS qty,
        i.stock_uom,
        i.opname_sort

    FROM `tabStock Ledger Entry` sle

    INNER JOIN `tabItem` i
        ON i.name = sle.item_code

    LEFT JOIN `tabWarehouse` w
        ON w.name = sle.warehouse

    LEFT JOIN `tabSerial and Batch Entry` sbe
        ON sbe.parent = sle.serial_and_batch_bundle

    LEFT JOIN `tabBatch` b
        ON b.name = sbe.batch_no

    WHERE
        {" AND ".join(conditions_batch)}
        {item_group_condition}

    GROUP BY
        sle.item_code,
        i.item_name,
        sle.warehouse,
        w.parent_warehouse,
        sbe.batch_no,
        b.manufacturing_date

    HAVING qty <> 0

    UNION ALL

    SELECT
        bin.item_code,
        i.item_name,
        bin.warehouse,
        w.parent_warehouse AS parent_warehouse,
        NULL AS batch_no,
        NULL AS manufacturing_date,
        bin.actual_qty AS qty,
        i.stock_uom,
        i.opname_sort

    FROM `tabBin` bin

    INNER JOIN `tabItem` i
        ON i.name = bin.item_code

    LEFT JOIN `tabWarehouse` w
        ON w.name = bin.warehouse

    WHERE
        {" AND ".join(conditions_non_batch)}
        {item_group_condition}

    HAVING qty <> 0

    ORDER BY
        opname_sort ASC,
        item_name ASC,
        warehouse ASC,
        manufacturing_date ASC
    """

    return frappe.db.sql(query, params, as_dict=True)