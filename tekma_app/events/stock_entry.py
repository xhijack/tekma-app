import frappe
def on_submit_stock_entry_production(doc, method):
    update_is_open(doc, 0)

def on_cancel_stock_entry_production(doc, method):
    update_is_open(doc, 1)


def update_is_open(doc, is_open = 1):
    if doc.stock_entry_type in ["Mincer", "Mixer", "Wrap"] and doc.prod_reference:
        frappe.db.set_value("Stock Entry", doc.prod_reference, "is_open", is_open, update_modified=False)