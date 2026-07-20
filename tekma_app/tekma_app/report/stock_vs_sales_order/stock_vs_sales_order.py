# Copyright (c) 2026, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import (
    add_days,
    date_diff,
    flt,
    formatdate,
    getdate,
    nowdate,
    cint
)

from tekma_app.custom.condition_builder import ConditionBuilder
from tekma_app.custom.stock import (
    get_realtime_stock,
)


MAX_DATE_COLUMNS = 31

DEFAULT_ITEM_GROUPS = [
    "FG",
    "MD",
]

EXCLUDED_SALES_ORDER_STATUSES = (
    "Closed",
    "Cancelled",
    "Completed",
)

STOCK_STATUS_FIELD = "status_stock"
OUTGOING_STOCK_STATUS = "Outgoing"


def execute(filters=None):
    filters = prepare_filters(filters)

    dates = get_dates(
        filters.from_date,
        filters.to_date,
    )

    columns = get_columns(dates)

    item_details = get_report_items(filters)

    if not item_details:
        return (
            columns,
            [],
            None,
            None,
            get_report_summary(
                data=[],
                shortage_items=0,
                total_sales_orders=0,
            ),
            1,
        )

    item_codes = list(item_details.keys())

    demand_rows = get_demand_rows(filters)

    stock_map, freezing_schedule = (
        get_stock_summary(
            filters,
            item_codes,
        )
    )

    demand_map = defaultdict(
        lambda: defaultdict(float)
    )

    sales_order_map = defaultdict(
        lambda: defaultdict(set)
    )

    item_sales_order_map = defaultdict(set)
    all_sales_orders = set()

    for demand in demand_rows:
        delivery_date = getdate(
            demand.delivery_date
        )

        item_code = demand.item_code
        sales_order = demand.sales_order

        demand_map[
            item_code
        ][delivery_date] += flt(
            demand.pending_qty
        )

        if sales_order:
            sales_order_map[
                item_code
            ][delivery_date].add(
                sales_order
            )

            item_sales_order_map[
                item_code
            ].add(
                sales_order
            )

            all_sales_orders.add(
                sales_order
            )

    sorted_item_codes = sorted(
        item_codes,
        key=lambda item_code: (
            item_details.get(
                item_code,
                frappe._dict(),
            ).get("opname_sort") or 0,
            item_details.get(
                item_code,
                frappe._dict(),
            ).get("item_name") or "",
            item_code,
        ),
    )

    data = []
    shortage_items = 0

    for item_code in sorted_item_codes:
        item = item_details.get(
            item_code,
            frappe._dict(),
        )

        stock = stock_map.get(
            item_code,
            frappe._dict(),
        )

        physical_stock = flt(
            stock.get("physical_stock")
        )

        ready_stock = flt(
            stock.get("ready_stock")
        )

        freezing_stock = flt(
            stock.get("freezing_stock")
        )

        running_balance = ready_stock

        running_balance = physical_stock
        total_pending = 0
        first_shortage_date = None

        item_sales_orders = sorted(
            item_sales_order_map.get(
                item_code,
                set(),
            )
        )

        row = frappe._dict({
            "item_code": item_code,
            "item_name": item.get(
                "item_name"
            ),
            "item_group": item.get(
                "item_group"
            ),
            "stock_uom": item.get(
                "stock_uom"
            ),
            "physical_stock": physical_stock,
            "ready_stock": ready_stock,
            "freezing_stock": freezing_stock,
            "total_so": len(
                item_sales_orders
            ),
            "sales_orders": item_sales_orders,
        })

        for delivery_date in dates:
            fieldname = get_date_fieldname(
                delivery_date
            )

            pending_qty = flt(
                demand_map[item_code].get(
                    delivery_date
                )
            )

            date_sales_orders = sorted(
                sales_order_map[
                    item_code
                ].get(
                    delivery_date,
                    set(),
                )
            )

            total_pending += pending_qty
            running_balance -= pending_qty

            row[fieldname] = pending_qty

            row[
                f"{fieldname}_balance"
            ] = running_balance

            row[
                f"{fieldname}_sales_orders"
            ] = date_sales_orders

            if (
                running_balance < 0
                and not first_shortage_date
            ):
                first_shortage_date = (
                    delivery_date
                )

        row.total_pending = total_pending

        row.balance = running_balance
        row.shortage_qty = max(
            -running_balance,
            0,
        )

        row.shortage_qty = max(
            -row.balance,
            0,
        )

        row.first_shortage_date = (
            first_shortage_date
        )
        if (
            filters.hide_no_order_item
            and total_pending <= 0
        ):
            continue

        if row.shortage_qty > 0:
            shortage_items += 1

        data.append(row)

    return (
        columns,
        data,
        None,
        None,
        get_report_summary(
            data=data,
            shortage_items=shortage_items,
            total_sales_orders=len(
                all_sales_orders
            ),
        ),
        1,
    )

def prepare_filters(filters=None):
    filters = frappe._dict(
        filters or {}
    )

    if not filters.get("company"):
        filters.company = (
            frappe.defaults.get_user_default(
                "Company"
            )
        )

    if not filters.company:
        frappe.throw(
            _("Company is required")
        )

    filters.from_date = getdate(
        filters.get("from_date")
        or nowdate()
    )

    filters.to_date = getdate(
        filters.get("to_date")
        or add_days(
            filters.from_date,
            2,
        )
    )

    if filters.from_date > filters.to_date:
        frappe.throw(
            _(
                "From Date cannot be after "
                "To Date"
            )
        )

    total_days = (
        date_diff(
            filters.to_date,
            filters.from_date,
        )
        + 1
    )

    if total_days > MAX_DATE_COLUMNS:
        frappe.throw(
            _(
                "Date range cannot exceed "
                "{0} days because each date "
                "is displayed as a column."
            ).format(MAX_DATE_COLUMNS)
        )

    filters.warehouse = normalize_list_filter(
        filters.get("warehouse")
    )

    filters.item_group = normalize_list_filter(
        filters.get("item_group")
    )

    if not filters.item_group:
        filters.item_group = list(
            DEFAULT_ITEM_GROUPS
        )

    filters.item = normalize_list_filter(
        filters.get("item")
    )
    
    filters.hide_no_order_item = cint(
        filters.get("hide_no_order_item")
    )

    return filters


def normalize_list_filter(value):
    if value is None or value == "":
        return []

    if isinstance(
        value,
        (list, tuple, set),
    ):
        return list(value)

    if isinstance(value, str):
        value = value.strip()

        if value.startswith("["):
            parsed = frappe.parse_json(
                value
            )

            if isinstance(
                parsed,
                (list, tuple),
            ):
                return list(parsed)

        return [value]

    return [value]


def get_dates(from_date, to_date):
    total_days = (
        date_diff(
            to_date,
            from_date,
        )
        + 1
    )

    return [
        getdate(
            add_days(
                from_date,
                offset,
            )
        )
        for offset in range(
            total_days
        )
    ]


def get_date_fieldname(delivery_date):
    delivery_date = getdate(
        delivery_date
    )

    return (
        "date_"
        + delivery_date.strftime(
            "%Y_%m_%d"
        )
    )


def get_columns(dates):
    columns = [
        {
            "label": _("Item Code"),
            "fieldname": "item_code",
            "fieldtype": "Link",
            "options": "Item",
            "width": 130,
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 220,
        },
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "fieldtype": "Link",
            "options": "Item Group",
            "width": 110,
        },
        {
            "label": _("UOM"),
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "options": "UOM",
            "width": 75,
        },
        {
            "label": _("Physical Stock"),
            "fieldname": "physical_stock",
            "fieldtype": "Float",
            "width": 110,
        },
        {
            "label": _("Ready Stock"),
            "fieldname": "ready_stock",
            "fieldtype": "Float",
            "width": 105,
        },
        {
            "label": _("Freezing"),
            "fieldname": "freezing_stock",
            "fieldtype": "Float",
            "width": 95,
        },
    ]

    for delivery_date in dates:
        columns.append({
            "label": formatdate(
                delivery_date,
                "dd MMM",
            ),
            "fieldname": get_date_fieldname(
                delivery_date
            ),
            "fieldtype": "Float",
            "width": 95,
        })

    columns.extend([
        {
            "label": _("Total SO"),
            "fieldname": "total_so",
            "fieldtype": "Int",
            "width": 85,
        },
        {
            "label": _("Total Pending"),
            "fieldname": "total_pending",
            "fieldtype": "Float",
            "width": 115,
        },
        {
            "label": _("Balance"),
            "fieldname": "balance",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("Shortage"),
            "fieldname": "shortage_qty",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": _("First Shortage"),
            "fieldname": "first_shortage_date",
            "fieldtype": "Date",
            "width": 120,
        },
    ])

    return columns


def get_demand_rows(filters):
    delivery_date_expression = """
        COALESCE(
            soi.delivery_date,
            so.delivery_date
        )
    """

    pending_qty_expression = """
        GREATEST(
            IFNULL(soi.stock_qty, 0)
            - IFNULL(soi.delivered_qty, 0),
            0
        )
    """

    builder = ConditionBuilder()

    (
        builder
        .where(
            "so.docstatus < 2"
        )
        .eq(
            "so.company",
            filters.company,
            key="demand_company",
        )
        .where(
            """
            IFNULL(so.status, '') NOT IN (
                'Closed',
                'Cancelled',
                'Completed'
            )
            """
        )
        .where(
            "i.is_stock_item = 1"
        )
        .where(
            "i.disabled = 0"
        )
        .where(
            f"{pending_qty_expression} > 0"
        )
        .between(
            delivery_date_expression,
            filters.from_date,
            filters.to_date,
            key="delivery_date",
        )
        .tree(
            "Warehouse",
            """
            COALESCE(
                NULLIF(soi.warehouse, ''),
                NULLIF(so.set_warehouse, '')
            )
            """,
            filters.warehouse,
            alias="demand_warehouses",
        )
        .tree(
            "Item Group",
            "i.item_group",
            filters.item_group,
            alias="demand_item_groups",
        )
        .in_(
            "soi.item_code",
            filters.item,
            key="demand_items",
        )
    )

    conditions, params = builder.build()

    return frappe.db.sql(
        f"""
        SELECT
            soi.item_code,

            {delivery_date_expression}
                AS delivery_date,

            so.name AS sales_order,

            SUM(
                {pending_qty_expression}
            ) AS pending_qty

        FROM `tabSales Order Item` soi

        INNER JOIN `tabSales Order` so
            ON so.name = soi.parent

        INNER JOIN `tabItem` i
            ON i.name = soi.item_code

        WHERE
            {" AND ".join(conditions)}

        GROUP BY
            soi.item_code,
            {delivery_date_expression},
            so.name

        ORDER BY
            {delivery_date_expression} ASC,
            soi.item_code ASC,
            so.name ASC
        """,
        params,
        as_dict=True,
    )


def get_report_items(filters):
    builder = ConditionBuilder()

    (
        builder
        .where(
            "i.is_stock_item = 1"
        )
        .where(
            "i.disabled = 0"
        )
        .tree(
            "Item Group",
            "i.item_group",
            filters.item_group,
            alias="report_item_groups",
        )
        .in_(
            "i.name",
            filters.item,
            key="report_items",
        )
    )

    conditions, params = builder.build()

    rows = frappe.db.sql(
        f"""
        SELECT
            i.name,
            i.item_name,
            i.item_group,
            i.stock_uom,
            i.opname_sort

        FROM `tabItem` i

        WHERE
            {" AND ".join(conditions)}

        ORDER BY
            IFNULL(i.opname_sort, 0) ASC,
            i.item_name ASC,
            i.name ASC
        """,
        params,
        as_dict=True,
    )

    return {
        row.name: row
        for row in rows
    }


def get_stock_summary(
    filters,
    item_codes,
):
    result = defaultdict(
        lambda: frappe._dict({
            "physical_stock": 0,
            "ready_stock": 0,
            "freezing_stock": 0,
        })
    )

    freezing_schedule = defaultdict(
        lambda: defaultdict(float)
    )

    if not item_codes:
        return result, freezing_schedule

    stock_filters = frappe._dict({
        "company": filters.company,
        "warehouse": filters.warehouse,
        "item_group": filters.item_group,
        "item": item_codes,
        "item_code": item_codes,

        # Harus detail supaya ready_date
        # per batch tetap tersedia.
        "summary": 0,

        "disabled_item": 0,
        "disabled_batch": 0,
        "ignore_empty_stock": 1,

        "freeze_days": 2,
        "as_of_date": filters.from_date,
    })

    stock_rows = get_realtime_stock(
        stock_filters
    )

    for stock_row in stock_rows:
        item_code = stock_row.get(
            "item_code"
        )

        qty = flt(
            stock_row.get("qty")
        )

        ready_qty = flt(
            stock_row.get("ready_qty")
        )

        freezing_qty = flt(
            stock_row.get("freezing_qty")
        )

        result[
            item_code
        ].physical_stock += qty

        result[
            item_code
        ].ready_stock += ready_qty

        result[
            item_code
        ].freezing_stock += (
            freezing_qty
        )

        ready_date = stock_row.get(
            "ready_date"
        )

        if (
            ready_date
            and freezing_qty
        ):
            freezing_schedule[
                item_code
            ][getdate(ready_date)] += (
                freezing_qty
            )

    return result, freezing_schedule

def get_report_summary(
    data,
    shortage_items,
    total_sales_orders,
):
    total_pending = sum(
        flt(row.get("total_pending"))
        for row in data
    )

    total_shortage = sum(
        flt(row.get("shortage_qty"))
        for row in data
    )

    return [
        {
            "value": len(data),
            "indicator": "Blue",
            "label": _("Items With Demand"),
            "datatype": "Int",
        },
        {
            "value": total_sales_orders,
            "indicator": "Blue",
            "label": _("Sales Orders"),
            "datatype": "Int",
        },
        {
            "value": shortage_items,
            "indicator": (
                "Red"
                if shortage_items
                else "Green"
            ),
            "label": _("Shortage Items"),
            "datatype": "Int",
        },
        {
            "value": total_pending,
            "indicator": "Blue",
            "label": _("Total Pending Qty"),
            "datatype": "Float",
        },
        {
            "value": total_shortage,
            "indicator": (
                "Red"
                if total_shortage
                else "Green"
            ),
            "label": _("Total Shortage Qty"),
            "datatype": "Float",
        },
    ]