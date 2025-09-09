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


def create_stock_entry_issued(doc, is_return=False):
    """
        `doc` is Delivery Note or Sales Invoice Document
    """
    se = frappe.new_doc("Stock Entry")
    se.purpose = "Material Issue"
    se.from_bom = 0
    se.company = doc.company
    se.posting_date = doc.posting_date
    se.posting_time = doc.posting_time
    se.stock_entry_type = "Material Issue" if is_return else "Material Receipt"
    se.doc_reference = doc.name
    se.items = []
    for item in doc.items:
        se.append("items", {
            "item_code": "Tiang",
            "item_name": item.item_name,
            "item_group": item.item_group,
            "qty": item.qty if not is_return else -item.qty,
            "s_warehouse": "Stores - MK"
        })
    if se.items:
        se.insert()
        se.submit()
        frappe.msgprint("Tiang dikeluarkan") if not is_return else "Tiang dikembalikan"


def move_tiang(doc):
    for item in doc.items:
        if item.tiang == "Tukar Tiang":
            create_stock_entry(doc, doc.is_return)
        elif item.tiang == "Dengan Tiang":
            create_stock_entry_issued(doc, doc.is_return)


def cancel_stock_entry(doc):
    se = frappe.get_all("Stock Entry", filters={"doc_reference": doc.name}, fields=["name"])
    for s in se:
        stock_entry = frappe.get_doc("Stock Entry", s.name)
        stock_entry.cancel()


def log_history_tiang(doc):
    ht = frappe.new_doc("History Tiang")
    ht.customer = doc.customer
    ht.date = doc.posting_date
    ht.document_type = doc.doctype
    ht.document = doc.name
    ht.qty = sum([item.qty for item in doc.items if item.tiang in ["Dengan Tiang","Tukar Tiang"]])
    ht.insert()
    ht.submit()


def cancel_log_history_tiang(doc):
    ht_names = frappe.get_all("History Tiang",
        filters={"document": doc.name, "docstatus": 1},
        pluck="name"
    )
    for nm in ht_names:
        ht = frappe.get_doc("History Tiang", nm)
        ht.flags.ignore_permissions = True
        ht.cancel()
    doc.flags.ignore_links = True


def delivery_note_on_submit(doc, method):
    move_tiang(doc)
    log_history_tiang(doc)


def delivery_note_on_cancel(doc, method):
    cancel_stock_entry(doc)
    cancel_log_history_tiang(doc)
    # cancel_linked_history_tiang(doc)


def sales_invoice_on_submit(doc, method):
    if doc.update_stock:
        move_tiang(doc)
        log_history_tiang(doc)
        

def sales_invoice_on_cancel(doc, method):
    if doc.update_stock:
        cancel_stock_entry(doc)
        cancel_log_history_tiang(doc)


def validate_ratio_for_valuation_rate_stock_entry(doc):
    total_ratio = 0
    for item in doc.items:
        item_detail = frappe.get_doc("Item", item.item_code)
        if item_detail.ratio != 0 and item.is_finished_item:
            total_ratio += item_detail.ratio * item.qty

    for item in doc.items:
        item_detail = frappe.get_doc("Item", item.item_code)
        if item_detail.ratio != 0 and item.is_finished_item:
            item.basic_rate = (doc.total_outgoing_value / total_ratio) * item_detail.ratio


def calculate_basic_rate(docname):
    doc = frappe.get_doc("Stock Entry", docname)
    respond = []
    total_ratio = 0
    for item in doc.items:
        item_detail = frappe.get_doc("Item", item.item_code)
        if item_detail.ratio != 0 and item.is_finished_item:
            total_ratio += item_detail.ratio * item.qty

    for item in doc.items:
        item_detail = frappe.get_doc("Item", item.item_code)
        if item_detail.ratio != 0 and item.is_finished_item:
            item.basic_rate = (doc.total_outgoing_value / total_ratio) * item_detail.ratio
            respond.append({'item_code': item.item_code, 'basic_rate': item.basic_rate})
    
    return respond


def stock_entry_on_validate(doc, method):
    if doc.stock_entry_type == "Wrap":
        total_qty = 0
        total_employee_qty = 0
        for item in doc.items:
            if item.is_finished_item:
                total_qty += item.qty

        for item in doc.employee_log:
            total_employee_qty += item.qty
        
        doc.difference_qty = total_qty - total_employee_qty
    # validate_ratio_for_valuation_rate_stock_entry(doc)