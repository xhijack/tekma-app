import frappe

def set_delivery_date_from_so(doc, method):
    if not doc.locations:
        return

    sales_order = None
    for row in doc.locations:
        if row.sales_order:
            sales_order = row.sales_order
            break

    if not sales_order:
        return

    so_date = frappe.db.get_value(
        "Sales Order",
        sales_order,
        "delivery_date"
    )

    # ✅ hanya warning, bukan block
    if so_date and doc.delivery_date and doc.delivery_date != so_date:
        frappe.msgprint(
            f"Delivery Date berbeda dengan Sales Order ({so_date})",
            indicator="orange"
        )