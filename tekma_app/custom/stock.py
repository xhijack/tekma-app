from tekma_app.custom.condition_builder import ConditionBuilder

def get_realtime_stock(filters):
    return RealtimeStock(filters).get_data()

class RealtimeStock:

    def __init__(self, filters=None):
        self.filters = filters or {}

    def build_conditions(self, warehouse_field, has_batch):
        builder = ConditionBuilder()

        (
            builder
            .tree(
                "Warehouse",
                warehouse_field,
                self.get_filters("warehouse"),
                alias="warehouses"
            )
            .tree(
                "Item Group",
                "i.item_group",
                self.get_filters("item_group"),
                alias="item_groups",
            )
            .in_(
                "i.name",
                self.get_filters("item"),
                key="items",
            )
            .eq(
                "i.disabled",
                self.get_filters("disabled"),
            )
            .eq("i.is_stock_item", 1)
        )

        disabled_item = self.get_filters("disabled_item")
        if not disabled_item:
            builder.eq("i.disabled", 0)

        if has_batch:
            builder.where("sle.is_cancelled = 0")

            disabled_batch = self.get_filters("disabled_batch")
            if not disabled_batch:
                builder.eq("b.disabled", 0)


        return builder.build()
    
    def get_data(self):
        query_batch, batch_params = self.query_batch()
        query_non_batch, non_batch_params = self.query_non_batch()

        params = {
            **batch_params,
            **non_batch_params,
        }

        summary = self.get_filters("summary")
        union_query = ""
        if not summary:
            union_query = f"""
                UNION ALL
                {query_batch}
            """
        query = f"""
            SELECT * FROM (
                {query_non_batch}
                {union_query}
            ) t
        """
        if self.get_filters("ignore_empty_stock"):
            query += " HAVING qty <> 0 "
        query += """
            ORDER BY
                t.opname_sort ASC,
                t.item_name ASC,
                t.warehouse ASC,
                t.manufacturing_date ASC
        """

        import frappe

        return frappe.db.sql(
            query,
            params,
            as_dict=True,
        )
    
    def query_non_batch(self):

        non_batch_conditions, non_batch_params = self.build_conditions(
            warehouse_field="bin.warehouse",
            has_batch=False,
        )

        summary = self.get_filters("summary")
        if not summary:
            non_batch_conditions.append("i.has_batch_no = 0")

        return f"""
            SELECT
                bin.item_code,
                i.item_name,
                bin.warehouse,
                w.parent_warehouse,
                NULL AS batch_no,
                NULL AS manufacturing_date,
                bin.actual_qty AS qty,
                i.stock_uom,
                i.opname_sort,
                i.disabled AS disabled_item,
                NULL AS disabled_batch

            FROM `tabBin` bin

            INNER JOIN `tabItem` i
                ON i.name = bin.item_code

            LEFT JOIN `tabWarehouse` w
                ON w.name = bin.warehouse

            WHERE {" AND ".join(non_batch_conditions)}
        """, non_batch_params
    
    def query_batch(self):
        batch_conditions, batch_params = self.build_conditions(
            warehouse_field="sle.warehouse",
            has_batch=True,
        )
        batch_conditions.append("i.has_batch_no = 1")

        return f"""
            SELECT
                sle.item_code,
                i.item_name,
                sle.warehouse,
                w.parent_warehouse,
                sbe.batch_no,
                b.manufacturing_date,
                SUM(sbe.qty) AS qty,
                i.stock_uom,
                i.opname_sort,
                i.disabled AS disabled_item,
                b.disabled AS disabled_batch

            FROM `tabStock Ledger Entry` sle

            INNER JOIN `tabItem` i
                ON i.name = sle.item_code

            LEFT JOIN `tabWarehouse` w
                ON w.name = sle.warehouse

            LEFT JOIN `tabSerial and Batch Entry` sbe
                ON sbe.parent = sle.serial_and_batch_bundle

            LEFT JOIN `tabBatch` b
                ON b.name = sbe.batch_no

            WHERE {" AND ".join(batch_conditions)}

            GROUP BY
                sle.item_code,
                i.item_name,
                sle.warehouse,
                sbe.batch_no,
                b.manufacturing_date
        """, batch_params
    
    def get_filters(self, filter):
        return self.filters.get(filter)
    