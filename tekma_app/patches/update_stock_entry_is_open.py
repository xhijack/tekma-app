import frappe

def execute():
    frappe.db.set_value("Stock Entry", {
        "is_open": 1,
        "docstatus": 1,
    }, "is_open", 0, update_modified=False)
