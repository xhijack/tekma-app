from typing import Final
import frappe

DT: Final = "Dengan Tiang"
TT: Final = "Tukar Tiang"


def make_log_history_tiang(customer, posting_date, doctype, docname, qty, condition, rate):
    ht = frappe.new_doc('History Tiang')
    ht.customer = customer
    ht.date = posting_date
    ht.document_type = doctype
    ht.document = docname
    ht.rate = rate
    ht.qty = qty
    ht.condition = condition

    ht.insert()
    ht.submit()
    return ht

def cancel_log_history_tiang(doc):
    ht_names = frappe.get_all("History Tiang",
        filters={"document": doc.name, "docstatus": 1},
        pluck="name"
    )
    for nm in ht_names:
        ht = frappe.get_doc("History Tiang", nm)
        ht.flags.ignore_permissions = True
        ht.cancel()



def validating_warehouse(doc, method):
    settings = frappe.get_single("Tiang Settings")

    item_tiang = settings.item_tiang
    customer_warehouse = settings.customer_warehouse
    tiang_warehouse = settings.tiang_warehouse
    tt_stock_entry = settings.tt_stock_entry

    if doc.stock_entry_type == tt_stock_entry and not doc.flags.skip_validate_wh:
        for item in doc.items:
            if item.item_code != item_tiang:
                frappe.throw(f"Item yg dipilih tidak sesuai, harus: {item_tiang}",)
            if item.customer is None:
                frappe.throw(f"Customer Harus di isi untuk menggunakan Stock Entry berjenis {tt_stock_entry}")
            if item.s_warehouse != customer_warehouse:
                frappe.throw(f"Gudang Source Warehouse harus {customer_warehouse}")
            if item.t_warehouse != tiang_warehouse:
                frappe.throw(f"Gudang Source Warehouse harus {tiang_warehouse}")

def get_item_with_tiang(items, only_fg=True):
    dt = []
    tt = []

    for item in items:
        if only_fg and item.item_group != "FG":
            continue

        if item.tiang == DT:
            dt.append(item)

        elif item.tiang == TT:
            tt.append(item)

    return [
        {"is_dt": True, "items": dt},
        {"is_dt": False, "items": tt},
    ]

def make_movement_stock_tiang(doctype, doc):
    is_outgoing = not doc.is_return
    if not is_outgoing:
        frappe.msgprint("Sales return tidak mengembalikan tiang. <b>Pastikan melakukan pencatatan</b>")
        # return

    settings = frappe.get_single("Tiang Settings")
    item_tiang = settings.item_tiang
    customer_warehouse = settings.customer_warehouse
    tiang_warehouse = settings.tiang_warehouse
    only_fg_item = settings.only_fg_item
    accumulate_items = settings.accumulate
    dt_stock_entry = settings.dt_stock_entry
    dt_stock_entry_against = settings.dt_stock_entry_against
    dt_account = settings.dt_account
    dt_series = settings.dt_series
    tt_stock_entry = settings.tt_stock_entry
    tt_account = settings.tt_account
    tt_series = settings.tt_series

    # validation
    if not all([
        item_tiang,
        customer_warehouse,
        tiang_warehouse,
    ]):
        return

    items_grouped = get_item_with_tiang(
        doc.items,
        only_fg_item
    )

    for group in items_grouped:
        items = group.get("items")

        if not items:
            continue

        is_dt = group.get("is_dt")

        # default TT
        stock_entry_type = tt_stock_entry
        account = tt_account
        naming_series = tt_series

        s_warehouse = (
            tiang_warehouse
            if is_outgoing
            else customer_warehouse
        )

        t_warehouse = (
            customer_warehouse
            if is_outgoing
            else tiang_warehouse
        )

        to_customer = doc.customer
        from_customer = doc.customer
        # DT override
        if is_dt:
            stock_entry_type = dt_stock_entry
            account = dt_account
            naming_series = dt_series

            purpose = frappe.get_value(
                "Stock Entry Type",
                stock_entry_type,
                "purpose"
            )
            # reverse issue saat return
            if purpose == "Material Issue" and not is_outgoing:
                if dt_stock_entry_against:
                    stock_entry_type = dt_stock_entry_against
                    purpose = frappe.get_value(
                        "Stock Entry Type",
                        stock_entry_type,
                        "purpose"
                    )
                else:
                    purpose = "Material Receipt"
                    stock_entry_type = "Material Receipt"
            s_warehouse = (
                tiang_warehouse
                if is_outgoing
                else None
            )

            t_warehouse = (
                None
                if is_outgoing
                else tiang_warehouse
            )

        else:
            purpose = frappe.get_value(
                "Stock Entry Type",
                stock_entry_type,
                "purpose"
            )

        # create stock entry
        se = frappe.new_doc("Stock Entry")
        if not is_dt:
            se.flags.skip_validate_wh = True
        se.flags.skip_event_submit = True
        se.stock_entry_type = stock_entry_type
        se.purpose = purpose
        se.naming_series = naming_series

        se.from_bom = 0
        se.company = doc.company
        se.posting_date = doc.posting_date
        se.posting_time = doc.posting_time

        se.delivery_note_id = doc.name
        if not accumulate_items:
            for item in items:
                qty = item.qty if is_outgoing else -item.qty
                se.append("items", {
                    "item_code": item_tiang,
                    # "item_name": item.item_name,
                    "qty": qty,
                    "s_warehouse": s_warehouse,
                    "t_warehouse": t_warehouse,
                    "expense_account": account,
                    "to_customer": to_customer,
                    "customer": from_customer
                })
                make_log_history_tiang(doc.customer, doc.posting_date, doc.doctype, doc.name, item.qty, TT if not is_dt else DT, item.tiang_rate if is_dt else None)
        else:
            qty = sum([item.qty for item in items])
            qty = qty if is_outgoing else qty * -1
            rate = 0
            if qty:
                rate = sum([item.tiang_rate * item.qty for item in items]) / qty
            se.append("items", {
                    "item_code": item_tiang,
                    # "item_name": item.item_name,
                    "qty": qty,
                    "s_warehouse": s_warehouse,
                    "t_warehouse": t_warehouse,
                    "expense_account": account,
                    "to_customer": to_customer,
                    "customer": from_customer
                })
            make_log_history_tiang(doc.customer, doc.posting_date, doc.doctype, doc.name, qty if is_outgoing else -qty, TT if not is_dt else DT, rate=rate if is_dt else None)
        se.insert()
        se.submit()
        
        frappe.msgprint(f"Berhasil {'Mengeluarkan' if is_outgoing else 'Mengembalikan'} Tiang", title="History Tiang")
        

def delivery_note_on_submit(doc, method):
    make_movement_stock_tiang("Delivery Note", doc)

def sales_invoice_on_submit(doc, method):
    make_movement_stock_tiang("Sales Invoice", doc)

# def delivery_note_on_cancel(doc, method):
#     cancel_log_history_tiang(doc)


def stock_entry_on_submit(doc, method):
    if not doc.flags.skip_event_submit:
        settings = frappe.get_single("Tiang Settings")
        tt_stock_entry = settings.tt_stock_entry
        if doc.stock_entry_type == tt_stock_entry:
            for item in doc.items:
                make_log_history_tiang(customer=item.customer, posting_date=doc.posting_date, doctype="Stock Entry", docname=doc.name, qty=-item.qty, condition="Tukar Tiang", rate=None)

# def stock_entry_on_cancel(doc, method):
#     cancel_log_history_tiang(doc)




def purchase_invoice_on_submit(doc, method):
    tiang_settings = frappe.get_single("Tiang Settings")
    party_links = frappe.get_list("Party Link",filters={"primary_party": doc.supplier, "primary_role": "Supplier"})
    if len(party_links) == 0:
        return
    customer_name = frappe.db.get_value("Party Link", party_links[0].name, "secondary_party")
    if doc.update_stock == 1:
        for item in doc.items:
            if item.item_code == tiang_settings.item_tiang:
                validate_get_tiang(customer_name, item.qty, condition="Dengan Tiang")
                make_log_history_tiang(customer=customer_name, posting_date=doc.posting_date, doctype="Purchase Invoice",docname=doc.name,qty=-item.qty, condition="Dengan Tiang", rate=item.rate)

def purchase_invoice_on_cancel(doc, method):
    cancel_log_history_tiang(doc)

def purchase_receipt_on_submit(doc, method):
    tiang_settings = frappe.get_single("Tiang Settings")
    party_links = frappe.get_list("Party Link",filters={"primary_party": doc.supplier, "primary_role": "Supplier"})
    if len(party_links) == 0:
        return
    customer_name = frappe.db.get_value("Party Link", party_links[0].name, "secondary_party")

    for item in doc.items:
        if item.item_code == tiang_settings.item_tiang:
            validate_get_tiang(customer_name, item.qty, condition="Dengan Tiang")
            make_log_history_tiang(customer=customer_name, posting_date=doc.posting_date, doctype="Purchase Receipt",docname=doc.name,qty=-item.qty, condition="Dengan Tiang", rate=item.rate)

def purchase_receipt_on_cancel(doc, method):
    cancel_log_history_tiang(doc)

def validate_get_tiang(customer, qty, condition="Dengan Tiang"):
    """
    Return total qty of History Tiang for a given customer with condition "Dengan Tiang".
    """
    if not customer:
        frappe.throw("Customer wajib diisi")

    total_qty = frappe.db.sql(
        """
        SELECT COALESCE(SUM(qty), 0)
        FROM `tabHistory Tiang`
        WHERE customer = %s
          AND `condition` = %s
          AND docstatus = 1
        """,
        (customer, condition)
    )[0][0] or 0

    total_qty = float(total_qty or 0)
    
    if total_qty < qty:
        frappe.throw(f"Stok tiang '{condition}' di pelanggan '{customer}' tidak dapat dibeli kembali. Tersedia: {total_qty}, dibutuhkan: {qty}")
