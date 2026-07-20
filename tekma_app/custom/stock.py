from collections import defaultdict

import frappe
from frappe.utils import cint, flt, getdate, nowdate

from tekma_app.custom.condition_builder import ConditionBuilder


def get_realtime_and_picked_stock(filters=None):
    filters = frappe._dict(filters or {})

    stock = get_realtime_stock(filters)
    picked = get_picked_stock(filters)

    return merge_stock_and_picked(stock, picked)



def get_realtime_stock(filters=None):
    return RealtimeStock(filters).get_data()


def get_picked_stock(filters=None):
    return PickedStock(filters).get_data()


def merge_stock_and_picked(stock, pick_items):
    picked_map = defaultdict(float)

    for row in pick_items:
        key = (
            row.get("item_code"),
            row.get("warehouse"),
            row.get("batch_no") or None,
        )

        picked_map[key] += flt(
            row.get("picked_qty")
        )

    result = []

    for row in stock:
        data = frappe._dict(row.copy())

        key = (
            data.get("item_code"),
            data.get("warehouse"),
            data.get("batch_no") or None,
        )

        physical_qty = flt(
            data.get("qty")
        )

        picked_qty = flt(
            picked_map.get(key)
        )

        data.physical_qty = physical_qty
        data.picked_qty = picked_qty
        data.available_qty = (
            physical_qty - picked_qty
        )

        data.actual_qty = data.available_qty

        result.append(data)

    return result

def get_freezing_stock(filters=None):
    filters = frappe._dict(
        filters or {}
    )

    filters.summary = 0

    rows = get_realtime_stock(
        filters
    )

    return [
        row
        for row in rows
        if flt(
            row.get("freezing_qty")
        ) != 0
    ]

class RealtimeStock:

    DEFAULT_FREEZE_DAYS = 2

    def __init__(self, filters=None):
        self.filters = frappe._dict(
            filters or {}
        )

        self.filters.freeze_days = cint(
            self.filters.get("freeze_days")
            or self.DEFAULT_FREEZE_DAYS
        )

        self.filters.as_of_date = getdate(
            self.filters.get("as_of_date")
            or nowdate()
        )

    def build_conditions(
        self,
        warehouse_field,
        has_batch,
    ):
        builder = ConditionBuilder()

        (
            builder
            .tree(
                "Warehouse",
                warehouse_field,
                self.get_filters("warehouse"),
                alias="warehouses",
            )
            .tree(
                "Item Group",
                "i.item_group",
                self.get_filters("item_group"),
                alias="item_groups",
            )
            .in_(
                "i.name",
                (
                    self.get_filters("item")
                    or self.get_filters("item_code")
                ),
                key="items",
            )
            .eq(
                "i.disabled",
                self.get_filters("disabled"),
            )
            .eq(
                "i.is_stock_item",
                1,
            )
        )

        if not self.get_filters(
            "disabled_item"
        ):
            builder.eq(
                "i.disabled",
                0,
            )

        if has_batch:
            builder.where(
                "sle.is_cancelled = 0"
            )

            builder.where(
                "sbe.batch_no IS NOT NULL"
            )

            if not self.get_filters(
                "disabled_batch"
            ):
                builder.eq(
                    "b.disabled",
                    0,
                )

        return builder.build()

    def get_query_and_params(self):
        query_non_batch, non_batch_params = (
            self.query_non_batch()
        )

        query_batch, batch_params = (
            self.query_batch()
        )

        params = {
            **non_batch_params,
            **batch_params,
        }

        union_query = f"""
            {query_non_batch}

            UNION ALL

            {query_batch}
        """

        if self.get_filters("summary"):
            query = f"""
                SELECT
                    lv.item_code,
                    MAX(lv.item_name)
                        AS item_name,

                    lv.warehouse,

                    MAX(lv.parent_warehouse)
                        AS parent_warehouse,

                    NULL AS batch_no,
                    NULL AS manufacturing_date,
                    NULL AS ready_date,

                    SUM(lv.qty)
                        AS qty,

                    SUM(lv.ready_qty)
                        AS ready_qty,

                    SUM(lv.freezing_qty)
                        AS freezing_qty,

                    CASE
                        WHEN SUM(
                            lv.freezing_qty
                        ) > 0
                        THEN 'Freezing'
                        ELSE 'Ready'
                    END AS freeze_status,

                    MAX(lv.stock_uom)
                        AS stock_uom,

                    MAX(lv.opname_sort)
                        AS opname_sort,

                    MAX(lv.disabled_item)
                        AS disabled_item,

                    NULL AS disabled_batch,

                    MAX(lv.item_group)
                        AS item_group

                FROM (
                    {union_query}
                ) lv

                GROUP BY
                    lv.item_code,
                    lv.warehouse
            """
        else:
            query = f"""
                SELECT *
                FROM (
                    {union_query}
                ) lv
            """

        query = f"""
            SELECT *
            FROM (
                {query}
            ) stock
        """

        if self.get_filters(
            "ignore_empty_stock"
        ):
            query += """
                WHERE
                    ABS(
                        IFNULL(stock.qty, 0)
                    ) > 0.000001
            """

        query += """
            ORDER BY
                stock.opname_sort ASC,
                stock.item_name ASC,
                stock.warehouse ASC,
                stock.ready_date ASC,
                stock.manufacturing_date ASC,
                stock.batch_no ASC
        """

        return query, params

    def get_data(self):
        query, params = (
            self.get_query_and_params()
        )

        return frappe.db.sql(
            query,
            params,
            as_dict=True,
        )

    def query_non_batch(self):
        conditions, params = (
            self.build_conditions(
                warehouse_field=(
                    "bin.warehouse"
                ),
                has_batch=False,
            )
        )

        conditions.append(
            "i.has_batch_no = 0"
        )

        return f"""
            SELECT
                bin.item_code,
                i.item_name,
                bin.warehouse,
                w.parent_warehouse,

                NULL AS batch_no,
                NULL AS manufacturing_date,
                NULL AS ready_date,

                bin.actual_qty AS qty,
                bin.actual_qty AS ready_qty,
                0 AS freezing_qty,

                'Ready' AS freeze_status,

                i.stock_uom,
                i.opname_sort,
                i.disabled AS disabled_item,

                NULL AS disabled_batch,

                i.item_group

            FROM `tabBin` bin

            INNER JOIN `tabItem` i
                ON i.name = bin.item_code

            LEFT JOIN `tabWarehouse` w
                ON w.name = bin.warehouse

            WHERE
                {" AND ".join(conditions)}
        """, params

    def query_batch(self):
        conditions, params = (
            self.build_conditions(
                warehouse_field=(
                    "sle.warehouse"
                ),
                has_batch=True,
            )
        )

        conditions.append(
            "i.has_batch_no = 1"
        )

        params.update({
            "freeze_days": (
                self.filters.freeze_days
            ),
            "freeze_as_of_date": (
                self.filters.as_of_date
            ),
        })

        ready_date_expression = """
            ADDDATE(
                b.manufacturing_date,
                %(freeze_days)s
            )
        """

        qty_expression = """
            SUM(
                IFNULL(sbe.qty, 0)
            )
        """

        return f"""
            SELECT
                sle.item_code,
                i.item_name,
                sle.warehouse,
                w.parent_warehouse,

                sbe.batch_no,
                b.manufacturing_date,

                {ready_date_expression}
                    AS ready_date,

                {qty_expression}
                    AS qty,

                CASE
                    WHEN
                        b.manufacturing_date
                            IS NULL
                    THEN {qty_expression}

                    WHEN
                        {ready_date_expression}
                            <= %(freeze_as_of_date)s
                    THEN {qty_expression}

                    ELSE 0
                END AS ready_qty,

                CASE
                    WHEN
                        b.manufacturing_date
                            IS NOT NULL
                        AND
                        {ready_date_expression}
                            > %(freeze_as_of_date)s
                    THEN {qty_expression}

                    ELSE 0
                END AS freezing_qty,

                CASE
                    WHEN
                        b.manufacturing_date
                            IS NOT NULL
                        AND
                        {ready_date_expression}
                            > %(freeze_as_of_date)s
                    THEN 'Freezing'

                    ELSE 'Ready'
                END AS freeze_status,

                i.stock_uom,
                i.opname_sort,

                i.disabled
                    AS disabled_item,

                b.disabled
                    AS disabled_batch,

                i.item_group

            FROM `tabStock Ledger Entry` sle

            INNER JOIN `tabItem` i
                ON i.name = sle.item_code

            LEFT JOIN `tabWarehouse` w
                ON w.name = sle.warehouse

            LEFT JOIN
                `tabSerial and Batch Entry` sbe
                ON sbe.parent =
                    sle.serial_and_batch_bundle

            LEFT JOIN `tabBatch` b
                ON b.name = sbe.batch_no

            WHERE
                {" AND ".join(conditions)}

            GROUP BY
                sle.item_code,
                i.item_name,
                sle.warehouse,
                w.parent_warehouse,
                sbe.batch_no,
                b.manufacturing_date,
                i.stock_uom,
                i.opname_sort,
                i.disabled,
                b.disabled,
                i.item_group
        """, params

    def get_filters(self, fieldname):
        return self.filters.get(
            fieldname
        )

class PickedStock:

    def __init__(self, filters=None):
        source_filters = frappe._dict(
            filters or {}
        )

        self.filters = frappe._dict({
            "company": source_filters.get(
                "company"
            ),
            "warehouse": source_filters.get(
                "warehouse"
            ),
            "item_code": (
                source_filters.get("item_code")
                or source_filters.get("item")
            ),
            "summary": source_filters.get(
                "summary"
            ),
        })

    def get_filter(self, fieldname):
        return self.filters.get(fieldname)

    def build_conditions(self):
        builder = ConditionBuilder()

        (
            builder
            .eq(
                "pl.company",
                self.get_filter("company"),
                key="picked_company",
            )
            .tree(
                "Warehouse",
                "pli.warehouse",
                self.get_filter("warehouse"),
                alias="picked_warehouses",
            )
            .in_(
                "i.name",
                self.get_filter("item_code"),
                key="picked_items",
            )
            .where(
                "pl.docstatus = 1"
            )
            .where(
                "pl.purpose = 'Delivery'"
            )
            .where(
                """
                IFNULL(pl.status, '') NOT IN (
                    'Cancelled',
                    'Completed'
                )
                """
            )
        )

        return builder.build()

    def get_query_and_params(self):
        conditions, params = (
            self.build_conditions()
        )

        pending_picked_expression = """
            GREATEST(
                IFNULL(pli.picked_qty, 0)
                - IFNULL(pli.delivered_qty, 0),
                0
            )
        """

        if self.get_filter("summary"):
            batch_select = "NULL"
            group_by = """
                pli.item_code,
                i.item_name,
                pli.warehouse
            """
        else:
            batch_select = "pli.batch_no"
            group_by = """
                pli.item_code,
                i.item_name,
                pli.warehouse,
                pli.batch_no
            """

        query = f"""
            SELECT
                pli.item_code,
                i.item_name,
                pli.warehouse,
                {batch_select} AS batch_no,
                SUM(
                    {pending_picked_expression}
                ) AS picked_qty

            FROM `tabPick List Item` pli

            INNER JOIN `tabPick List` pl
                ON pl.name = pli.parent

            INNER JOIN `tabItem` i
                ON i.name = pli.item_code

            WHERE
                {" AND ".join(conditions)}

            GROUP BY
                {group_by}

            HAVING
                picked_qty > 0

            ORDER BY
                i.item_name ASC,
                pli.warehouse ASC,
                batch_no ASC
        """

        return query, params

    def get_data(self):
        query, params = (
            self.get_query_and_params()
        )

        return frappe.db.sql(
            query,
            params,
            as_dict=True,
        )