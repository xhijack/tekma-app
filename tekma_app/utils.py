import frappe

def create_stock_entry(doc, is_return=False):
    """
        `doc` is Delivery Note or Sales Invoice Document
    """
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Transfer"
    se.from_bom = 0
    se.company = doc.company
    se.posting_date = doc.posting_date
    se.posting_time = doc.posting_time
    se.stock_entry_type = "Material Transfer"
    se.doc_reference = doc.name
    se.items = []
    for item in doc.items:
        se.append("items", {
            "item_code": "Tiang",
            "item_name": item.item_name,
            "item_group": item.item_group,
            "qty": item.qty if not is_return else -item.qty,
            "s_warehouse": "Stores - MK" if not is_return else "Pelanggan - MK",
            "t_warehouse": "Pelanggan - MK" if not is_return else "Stores - MK",
            "to_customer": doc.customer if not is_return else None,
            "customer": doc.customer if is_return else None,
        })
    se.insert()
    se.submit()
    frappe.msgprint("Tiang dikeluarkan")

def move_tiang(doc):
    for item in doc.items:
        if item.tiang == "Dengan Tiang":
            create_stock_entry(doc, doc.is_return)

def cancel_stock_entry(doc):
    se = frappe.get_all("Stock Entry", filters={"doc_reference": doc.name}, fields=["name"])
    for s in se:
        stock_entry = frappe.get_doc("Stock Entry", s.name)
        stock_entry.cancel()

def delivery_note_on_submit(doc, method):
    move_tiang(doc)

def delivery_note_on_cancel(doc, method):
    cancel_stock_entry(doc) 

def sales_invoice_on_submit(doc, method):
    if doc.update_stock:
        move_tiang(doc)

def sales_invoice_on_cancel(doc, method):
    if doc.update_stock:
        cancel_stock_entry(doc)