from collections import defaultdict

from tekma_app.custom.condition_builder import ConditionBuilder

def get_relatime_and_picked_stock(filters):
    stock = get_realtime_stock(filters)
    picked = get_picked_stock(filters)
    
    return merge_stock_and_picked(stock, picked)

def get_picked_stock(filters):
    return PickedStock(filters).get_data()


def get_realtime_stock(filters):
    return RealtimeStock(filters).get_data()

def merge_stock_and_picked(stock, pick_items):

    picked_map = defaultdict(float)

    for row in pick_items:
        key = (
            row["item_code"],
            row["warehouse"],
            row["batch_no"],
        )
        picked_map[key] += float(row.get("picked_qty") or 0)

    result = []

    for row in stock:
        data = row.copy()

        key = (
            data["item_code"],
            data["warehouse"],
            data["batch_no"],
        )

        picked_qty = picked_map.get(key, 0)

        data["picked_qty"] = picked_qty
        data["actual_qty"] = (data.get("qty") or 0) - picked_qty

        result.append(data)
    return result



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
    def get_query_and_params(self):
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
            ) lv
        """
        if self.get_filters("ignore_empty_stock"):
            query += " HAVING qty <> 0 "
        query += """
            ORDER BY
                lv.opname_sort ASC,
                lv.item_name ASC,
                lv.warehouse ASC,
                lv.manufacturing_date ASC
        """

        return query, params
    
    def get_data(self):
        query, params = self.get_query_and_params()    
        
        import frappe

        data = frappe.db.sql(
            query,
            params,
            as_dict=True,
        )
        return data
    
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
                NULL AS disabled_batch,
                i.item_group

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
                b.disabled AS disabled_batch,
                i.item_group

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
    


class PickedStock(RealtimeStock):
    def __init__(self, filters=None):
        filters = {
            "warehouse": filters.get("warehouse"),
            "item_code": filters.get("item_code"),
            "summary": filters.get("summary")
        }
        super().__init__(filters)

    def get_query_and_params(self):
        conditions, params = self.build_conditions()
        conditions.append("pl.docstatus = 1")
        conditions.append("pl.status = 'Open'")
        
        select = """
                pli.batch_no AS batch_no,
                pli.picked_qty
        """

        # validate summary
        if self.get_filters("summary"):
            select = """
                NULL AS batch_no,
                SUM(pli.picked_qty) AS picked_qty
            """
        query = f"""
            SELECT
                pl.name AS pick_list,
                pl.status,
                pl.docstatus,
                pli.item_code,
                i.item_name,
                pli.warehouse,
                {select}

            FROM `tabPick List Item` pli

            INNER JOIN `tabPick List` pl
                ON pl.name = pli.parent

            INNER JOIN `tabItem` i
                ON i.name = pli.item_code

            WHERE
                {" AND ".join(conditions)}

            GROUP BY
                item_code, warehouse, batch_no
        """

        return query, params
    
    def build_conditions(self):
        builder = ConditionBuilder()

        return builder.tree("Warehouse", "pli.warehouse", self.get_filters("warehouse")).in_("i.item_code", self.get_filters("item_code")).build()