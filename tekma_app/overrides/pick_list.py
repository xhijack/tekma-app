import frappe
from frappe.utils import getdate

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
    if so_date and doc.delivery_date:
        if getdate(doc.delivery_date) != getdate(so_date):
            frappe.msgprint(
                f"Delivery Date berbeda dengan Sales Order ({so_date})",
                indicator="orange"
            )
        
def set_keterangan(doc, method):
    if doc.catatan_untuk_gudang:
        return

    for row in doc.locations or []:
        if row.sales_order:
            so = frappe.get_doc("Sales Order", row.sales_order)
            if so.keterangan:
                doc.catatan_untuk_gudang = so.keterangan
            break