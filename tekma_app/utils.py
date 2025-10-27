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
    se.stock_entry_type = "Material Receipt" if is_return else "Material Issue"
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
    for item in doc.items:
        if item.tiang in ["Dengan Tiang","Tukar Tiang"]:
            ht = frappe.new_doc("History Tiang")
            ht.customer = doc.customer
            ht.date = doc.posting_date
            ht.document_type = doc.doctype
            ht.document = doc.name
            ht.rate = item.tiang_rate
            ht.qty = item.qty # sum([item.qty for item in doc.items if item.tiang in ["Dengan Tiang","Tukar Tiang"]])
            ht.rate = item.tiang_rate
            ht.condition = item.tiang
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


# tekma_app/utils.py
import frappe
from decimal import Decimal, ROUND_HALF_UP

def _compute_core(finished_items, total_rm_cost, rounding=0):
    total_rm_cost = Decimal(str(total_rm_cost))
    total_ratio_units = Decimal(0)
    norm = []
    for it in finished_items:
        qty = Decimal(str(it.get("qty") or 0))
        ratio = Decimal(str(it.get("ratio") or 1))
        if qty <= 0 or ratio <= 0:
            frappe.throw(f"Qty/Ratio harus > 0 untuk item {it.get('item_code')}")
        ru = qty * ratio
        total_ratio_units += ru
        norm.append({**it, "qty": qty, "ratio": ratio, "ratio_units": ru})

    if total_ratio_units == 0:
        frappe.throw("Total ratio units = 0, tidak bisa membagi biaya")

    cpru = total_rm_cost / total_ratio_units  # cost per ratio-unit
    qz = "1" if not rounding else f"1.{'0'*int(rounding)}"

    res = {}
    for it in norm:
        per_unit = (cpru * it["ratio"]).quantize(Decimal(qz), rounding=ROUND_HALF_UP)
        total = (per_unit * it["qty"]).quantize(Decimal(qz), rounding=ROUND_HALF_UP)
        res[it["item_code"]] = {
            "qty": float(it["qty"]),
            "ratio": float(it["ratio"]),
            "valuation_rate": float(per_unit),
            "total_cost": float(total),
        }

    sum_alloc = sum(v["total_cost"] for v in res.values())
    res["_meta"] = {
        "total_rm_cost": float(total_rm_cost),
        "sum_allocated": float(sum_alloc),
        "difference": float(total_rm_cost - Decimal(str(sum_alloc))),
    }
    return res


@frappe.whitelist()
def compute_valuation_rates(doc=None, rounding: int = 0, ratio_field: str = "ratio"):
    """
    Ambil ratio dari:
      - baris Stock Entry Detail (field 'ratio' / 'custom_ratio') JIKA ada
      - JIKA tidak ada → ambil dari master Item (field di parameter `ratio_field`, default: 'ratio').
    RM = baris punya s_warehouse (source), FG = baris punya t_warehouse (target).
    Return: { item_code: {qty, ratio, valuation_rate, total_cost}, _meta: {...} }
    """
    if not doc:
        frappe.throw("Parameter doc wajib diisi")
    doc = frappe.parse_json(doc)

    rows = doc.get("items") or []

    # 1) Raw Materials (keluar gudang)
    rm_rows = [r for r in rows if r.get("s_warehouse") and not r.get("t_warehouse")]
    if not rm_rows:
        frappe.throw("Tidak ditemukan baris Raw Material (s_warehouse terisi).")

    total_rm_cost = Decimal(0)
    for r in rm_rows:
        qty = Decimal(str(r.get("qty") or 0))
        rate = r.get("basic_rate") or r.get("valuation_rate") or r.get("rate") or 0
        total_rm_cost += qty * Decimal(str(rate))

    if total_rm_cost <= 0:
        frappe.throw("Total biaya Raw Material = 0. Pastikan basic_rate/valuation_rate baris RM terisi.")

    # 2) Finished Goods (masuk gudang)
    fg_rows = [r for r in rows if r.get("t_warehouse") and not r.get("s_warehouse")]
    if not fg_rows:
        frappe.throw("Tidak ditemukan baris Finished Goods (t_warehouse terisi).")

    # siapkan ratio dari Item master bila tidak ada di row
    item_codes = list({r.get("item_code") for r in fg_rows if r.get("item_code")})
    ratios_by_item = {code: 1 for code in item_codes}
    if item_codes:
        # ambil custom field ratio pada Item
        fields = ["name", ratio_field]
        for it in frappe.get_all("Item", filters={"name": ["in", item_codes]}, fields=fields):
            v = it.get(ratio_field)
            if v not in (None, ""):
                try:
                    ratios_by_item[it["name"]] = float(v)
                except Exception:
                    pass  # fallback 1 jika tidak bisa di-cast

    finished = []
    for r in fg_rows:
        ratio = r.get("ratio") or r.get("custom_ratio") or ratios_by_item.get(r.get("item_code"), 1)
        finished.append({
            "item_code": r.get("item_code"),
            "qty": r.get("qty"),
            "ratio": ratio,
        })

    return _compute_core(finished, total_rm_cost, rounding=int(rounding or 0))
