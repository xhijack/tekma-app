import frappe
from frappe.utils import flt
from terbilang import Terbilang


def get_terbilang(amount):
    t = Terbilang()
    t.parse(amount)
    return t.getresult()

from decimal import Decimal

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
    # qz = "1" if not rounding else f"1.{'0'*int(rounding)}"
    res = {}
    for it in norm:
        # per_unit = (cpru * it["ratio"]).quantize(Decimal(qz))
        # total = (per_unit * it["qty"]).quantize(Decimal(qz))
        per_unit = (cpru * it["ratio"])
        total = (per_unit * it["qty"])
        res[it["item_code"]] = {
            "qty": float(it["qty"]),
            "ratio": float(it["ratio"]),
            "valuation_rate": float(per_unit),
            "total_cost": float(total),
        }
    print(total_rm_cost)
    sum_alloc = sum(v["total_cost"] for v in res.values())
    print(sum_alloc)
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
        # print(r)
        qty = Decimal(str(r.get("qty") or 0))
        rate = r.get("basic_rate") or r.get("valuation_rate") or r.get("rate") or 0
        print(qty, frappe.format(rate, {"fieldtype": "Currency"}))
        total_rm_cost += qty*Decimal(str(rate)) * Decimal(str(r.get("conversion_factor")))

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


def sales_order_autofill_pembayaran(doc, method):
    if doc.customer and not doc.metode_pembayaran_customer:
        metode = frappe.db.get_value(
            "Customer",
            doc.customer,
            "metode_pembayaran_customer"
        )
        if metode:
            doc.metode_pembayaran_customer = metode
            
_EXCLUDED_FROM_BALANCE_CHECK = {"Material Receipt", "Material Issue"}

def _validate_value_balance(doc):
    if doc.purpose in _EXCLUDED_FROM_BALANCE_CHECK:
        return
    diff = flt(doc.value_difference or 0)
    
    if not(-1 < abs(diff) < 1):
        frappe.throw(
            f"Stock Entry tipe <b>{doc.stock_entry_type}</b> harus balance "
            f"(nilai masuk = nilai keluar). Selisih saat ini: <b>{diff}</b>. "
            "Pastikan semua baris sudah terisi basic_rate/valuation_rate dengan benar."
        )


def stock_entry_on_validate(doc, method):
    _validate_value_balance(doc)

    if doc.stock_entry_type == "Wrap":
        total_qty = 0
        total_employee_qty = 0
        for item in doc.items:
            if item.is_finished_item:
                total_qty += item.qty

        for item in doc.employee_log:
            total_employee_qty += item.qty
        
        doc.difference_qty = total_qty - total_employee_qty