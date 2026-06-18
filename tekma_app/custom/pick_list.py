
import frappe


from frappe.utils import get_link_to_form

def validate_sales_order_delivery(doc, event):
    if doc.purpose == "Delivery":
        for loc in doc.locations:
            if not loc.sales_order:
                frappe.throw("Item {0} row #{1}: Sales Order required for Pick List with purpose Delivery".format(loc.item_code, loc.idx))

def validate_stock_soft_reservation(doc, event):
    for row in doc.locations:
        if not row.item_code or not row.warehouse:
            continue

        if frappe.db.get_value("Item", row.item_code, "has_batch_no"):
            _validate_batch_item(doc, row)
        else:
            _validate_non_batch_item(doc, row)




# =========================
# SHARED HELPERS
# =========================

def _get_reserved(doc, item_code, warehouse, batch_no=None):
    conditions = """
        pl.status = 'Open'
        AND pli.item_code = %s
        AND pli.warehouse = %s
        AND pl.name != %s
    """

    params = [item_code, warehouse, doc.name]

    if batch_no:
        conditions += " AND pli.batch_no = %s"
        params.append(batch_no)

    return frappe.db.sql(f"""
        SELECT
            pl.name as pick_list,
            SUM(pli.qty) as qty
        FROM `tabPick List Item` pli
        JOIN `tabPick List` pl ON pl.name = pli.parent
        WHERE {conditions}
        GROUP BY pl.name
    """, tuple(params), as_dict=True)


def _build_picklist_table(reserved_data):
    rows = "".join(
        f"<tr><td>{get_link_to_form('Pick List', d.pick_list)}</td><td>{d.qty}</td></tr>"
        for d in reserved_data
    )

    return rows or "<tr><td colspan='2'>No reservation</td></tr>"


def _raise_stock_error(title, context_rows, reserved_data):
    table_context = "".join(
        f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"
        for k, v in context_rows
    )

    frappe.throw(f"""
        <div style="font-size:14px;">
            <b>❌ {title}</b>
            <hr>

            <table style="width:100%; margin-bottom:10px;">
                {table_context}
            </table>

            <b>Used by Pick List</b>
            <table class="table table-bordered">
                <tr>
                    <th>Pick List</th>
                    <th>Qty</th>
                </tr>
                {_build_picklist_table(reserved_data)}
            </table>
        </div>
    """)


# =========================
# BATCH VALIDATION
# =========================

def _validate_batch_item(doc, row):
    if not row.batch_no:
        frappe.throw(f"Batch wajib untuk item {row.item_code}")

    valid = frappe.db.exists("Batch", {
        "name": row.batch_no,
        "item": row.item_code
    })

    if not valid:
        frappe.throw(f"Batch {row.batch_no} tidak valid untuk item {row.item_code}")

    reserved_data = _get_reserved(
        doc,
        row.item_code,
        row.warehouse,
        row.batch_no
    )

    reserved = sum(d.qty for d in reserved_data)

    actual = frappe.db.get_value("Batch", row.batch_no, "batch_qty") or 0
    available = actual - reserved

    if row.qty > available:
        _raise_stock_error(
            "Batch Stock Tidak Cukup",
            [
                ("Item", row.item_code),
                ("Batch", row.batch_no),
                ("Available", available),
                ("Requested", row.qty),
            ],
            reserved_data
        )


# =========================
# NON-BATCH VALIDATION
# =========================

def _validate_non_batch_item(doc, row):
    reserved_data = _get_reserved(doc, row.item_code, row.warehouse)

    reserved = sum(d.qty for d in reserved_data)

    actual = frappe.db.get_value(
        "Bin",
        {"item_code": row.item_code, "warehouse": row.warehouse},
        "actual_qty"
    ) or 0

    available = actual - reserved

    if row.qty > available:
        _raise_stock_error(
            "Stock Tidak Cukup",
            [
                ("Item", row.item_code),
                ("Warehouse", row.warehouse),
                ("Available", available),
                ("Requested", row.qty),
            ],
            reserved_data
        )

import frappe
import json

@frappe.whitelist()
def validate_sales_order_qty(doc):
    if isinstance(doc, str):
        doc = frappe._dict(json.loads(doc))

    locations = doc.get("locations", [])

    grouped = {}

    for row in locations:
        row = frappe._dict(row)

        if not row.sales_order_item:
            continue

        key = row.sales_order_item

        grouped.setdefault(key, {
            "sales_order": row.sales_order,
            "sales_order_item": key,
            "item_code": row.item_code,
            "qty": 0,
            "rows": []
        })

        grouped[key]["qty"] += (row.qty or 0)
        grouped[key]["rows"].append(row)

    if not grouped:
        return []

    so_items = frappe.get_all(
        "Sales Order Item",
        filters={"name": ["in", list(grouped.keys())]},
        fields=["name", "qty"]
    )

    so_map = {d.name: d for d in so_items}

    errors = []

    for so_item, picked in grouped.items():
        so_data = so_map.get(so_item)

        if not so_data:
            continue

        so_qty = so_data.qty or 0
        picked_qty = picked["qty"] or 0

        diff = round(picked_qty - so_qty, 6)

        if diff != 0:
            errors.append({
                "sales_order": picked["sales_order"],
                "sales_order_item": so_item,
                "item_code": picked["item_code"],
                "so_qty": so_qty,
                "picked_qty": picked_qty,
                "diff": diff
            })

    return errors

@frappe.whitelist()
def get_pick_list_summary():
    pick_list = frappe.form_dict.get("pick_list")

    if not pick_list:
        frappe.throw("Pick List is required")

    data = frappe.db.sql("""
        SELECT
            pli.sales_order,
            so.customer,
            pli.sales_order_item,
            pli.item_code,
            soi.item_name,
            soi.qty AS so_qty,
            SUM(pli.qty) AS picked_qty
        FROM `tabPick List Item` pli
        INNER JOIN `tabSales Order Item` soi
            ON soi.name = pli.sales_order_item
        INNER JOIN `tabSales Order` so
            ON so.name = pli.sales_order
        WHERE
            pli.parent = %(pick_list)s
            AND IFNULL(pli.sales_order_item, '') != ''
        GROUP BY pli.sales_order_item
        ORDER BY
            pli.sales_order,
            pli.item_code
    """, {
        "pick_list": pick_list
    }, as_dict=True)


    for row in data:
        row["diff_qty"] = float(row.get("picked_qty") or 0) - float(row.get("so_qty") or 0)

    return data