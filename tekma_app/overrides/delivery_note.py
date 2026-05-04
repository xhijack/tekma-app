import frappe

def set_keterangan(doc, method):
    if doc.remarks:
        return

    sales_orders = set()

    for row in doc.locations or []:
        if row.sales_order:
            sales_orders.add(row.sales_order)

    if not sales_orders:
        return

    pick_lists = frappe.db.sql("""
        SELECT pl.name, pl.catatan_untuk_gudang
        FROM `tabPick List` pl
        LEFT JOIN `tabPick List Item` pli ON pli.parent = pl.name
        WHERE pl.docstatus = 1
        AND (
            pl.sales_order IN %(so)s
            OR pli.sales_order IN %(so)s
        )
        ORDER BY pl.creation DESC
        LIMIT 1
    """, {"so": tuple(sales_orders)}, as_dict=True)

    if pick_lists:
        catatan = pick_lists[0].get("catatan_untuk_gudang")
        if catatan:
            doc.remarks = catatan