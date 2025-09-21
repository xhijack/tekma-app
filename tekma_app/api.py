import frappe
from frappe.utils import flt

@frappe.whitelist()
def get_ar_summary_by_customer(company, customer):
    """Return credit_limit & outstanding_amount saja."""
    credit_limit = flt(frappe.db.get_value(
        "Customer Credit Limit",
        {"parent": customer, "company": company},
        "credit_limit"
    ) or 0)

    res = frappe.db.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "company": company, "customer": customer},
        fields=["sum(outstanding_amount) as outstanding"],
        limit_page_length=1,
    )
    outstanding_amount = flt((res[0].get("outstanding") if res else 0) or 0)

    return {
        "credit_limit": credit_limit,
        "outstanding_amount": outstanding_amount
    }


@frappe.whitelist()
def get_ar_invoices_by_customer(company, customer):
    """
    AR details with credit-note application:
      - invoices: SI (docstatus=1, outstanding>0) + adjusted_outstanding setelah dikurangi return yg link ke invoice tsb (return_against)
      - credit_notes remaining: sisa kredit dari SI Return (is_return=1) yg BELUM habis terpakai untuk invoice asal
        + termasuk CN tanpa return_against (credit note berdiri sendiri)
      - advances: Payment Entry Receive (unallocated_amount>0)
      - totals & totals_adjusted & totals_extended (net receivable)
    Semua angka di mata uang company (pakai base_* / outstanding_amount SI).
    """

    company_currency = frappe.db.get_value("Company", company, "default_currency") or "IDR"

    # 1) Ambil invoice outstanding (positif)
    inv_rows = frappe.db.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "company": company, "customer": customer, "outstanding_amount": [">", 0]},
        fields=["name", "posting_date", "base_grand_total", "outstanding_amount", "remarks"],
        order_by="posting_date desc",
        limit_page_length=500,
    )

    # 2) Ambil semua RETURN (credit note) yang masih punya outstanding negatif (available)
    #    Sertakan return_against utk pairing ke invoice asal.
    cn_rows = frappe.db.get_all(
        "Sales Invoice",
        filters={"docstatus": 1, "company": company, "customer": customer, "is_return": 1, "outstanding_amount": ["<", 0]},
        fields=["name", "posting_date", "outstanding_amount", "return_against"],
        order_by="posting_date desc",
        limit_page_length=1000,
    )

    # Susun credit note map per invoice asal
    # Simpan objek per CN agar bisa hitung "applied" per CN (bukan hanya agregat per invoice)
    cn_by_inv = {}   # {return_against: [cn_obj,...]}
    cn_objects = {}  # {cn_name: {"name":..., "posting_date":..., "available":..., "applied":0, "return_against":...}}
    for cn in cn_rows:
        available = flt(-cn.outstanding_amount)  # outstanding negatif -> available positif
        obj = {
            "name": cn.name,
            "posting_date": cn.posting_date,
            "available": available,
            "applied": 0.0,
            "return_against": cn.return_against or None,
        }
        cn_objects[cn.name] = obj
        if cn.return_against:
            cn_by_inv.setdefault(cn.return_against, []).append(obj)

    # Terapkan kredit ke masing-masing invoice asalnya
    invoices = []
    tot_gt = tot_paid = tot_out = 0.0
    total_applied_from_returns = 0.0

    # Urutkan CN per invoice (opsional: terbaru dulu)
    for lst in cn_by_inv.values():
        lst.sort(key=lambda x: x["posting_date"], reverse=True)

    for inv in inv_rows:
        grand_total = flt(inv.base_grand_total)
        outstanding = flt(inv.outstanding_amount)
        paid_amount = flt(grand_total - outstanding)

        applied_credit = 0.0
        if inv.name in cn_by_inv:
            need = outstanding
            for cn in cn_by_inv[inv.name]:
                if need <= 0:
                    break
                avail = cn["available"] - cn["applied"]
                if avail <= 0:
                    continue
                use = min(avail, need)
                cn["applied"] += use
                applied_credit += use
                need -= use

        adjusted_outstanding = max(0.0, outstanding - applied_credit)
        total_applied_from_returns += applied_credit

        invoices.append({
            "name": inv.name,
            "posting_date": inv.posting_date,
            "grand_total": grand_total,
            "paid_amount": paid_amount,
            "outstanding_amount": outstanding,          # original
            "applied_credit": applied_credit,           # berapa kredit yg dipakai utk inv ini
            "adjusted_outstanding": adjusted_outstanding,  # yang dipakai di UI
            "remarks": getattr(inv, "remarks", "") or ""
        })

        tot_gt += grand_total
        tot_paid += paid_amount
        tot_out += outstanding

    # 3) Hitung sisa credit note per dokumen (remaining)
    credit_notes_remaining = []
    total_credit_remaining = 0.0
    for cn in cn_objects.values():
        remaining = flt(cn["available"] - cn["applied"])
        if remaining > 0:
            credit_notes_remaining.append({
                "name": cn["name"],
                "posting_date": cn["posting_date"],
                "return_against": cn["return_against"],
                "available_amount": remaining,
            })
            total_credit_remaining += remaining

    # 4) Advances / Dana Menggantung
    adv_rows = frappe.db.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "company": company,
            "party_type": "Customer",
            "party": customer,
            "payment_type": "Receive",
            "unallocated_amount": [">", 0],
        },
        fields=["name", "posting_date", "unallocated_amount"],
        order_by="posting_date desc",
        limit_page_length=500,
    )
    advances = []
    total_unallocated = 0.0
    for r in adv_rows:
        amt = flt(r.unallocated_amount)
        advances.append({"name": r.name, "posting_date": r.posting_date, "unallocated_amount": amt})
        total_unallocated += amt

    # 5) Totals
    invoices_outstanding_adjusted = sum(flt(i["adjusted_outstanding"]) for i in invoices)
    net_receivable = flt(invoices_outstanding_adjusted - total_credit_remaining - total_unallocated)

    return {
        "currency": company_currency,
        "invoices": invoices,  # berisi adjusted_outstanding & applied_credit
        "totals": {
            "grand_total": tot_gt,
            "paid_amount": tot_paid,
            "outstanding_amount": tot_out,  # original total outstanding (belum dikurangi return)
            "applied_credit_from_returns": total_applied_from_returns,
        },
        "credit_notes": credit_notes_remaining,  # hanya sisa yg belum terpakai
        "advances": advances,
        "totals_adjusted": {
            "invoices_outstanding_adjusted": invoices_outstanding_adjusted
        },
        "totals_extended": {
            "invoices_outstanding_adjusted": invoices_outstanding_adjusted,
            "credit_note_available": total_credit_remaining,
            "advance_unallocated": total_unallocated,
            "net_receivable": net_receivable,
        },
    }

@frappe.whitelist()
def get_item_price_history(company, item_code, customer=None, limit=100):
    """
    Riwayat harga item dari Sales Invoice yang sudah submit (docstatus=1).
    Kolom yang dikembalikan dipangkas sesuai permintaan (tanpa customer, currency, price_list_rate, net_rate).
    """
    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100
    limit = min(max(limit, 1), 500)  # safety: 1..500

    params = {
        "company": company,
        "item_code": item_code,
    }

    extra_customer_cond = ""
    if customer:
        extra_customer_cond = " AND si.customer = %(customer)s "
        params["customer"] = customer

    rows = frappe.db.sql(
        """
        SELECT
            si.name            AS invoice,
            si.posting_date    AS posting_date,
            sii.item_code      AS item_code,
            sii.item_name      AS item_name,
            sii.qty            AS qty,
            sii.uom            AS uom,
            sii.discount_percentage,
            sii.rate,
            sii.net_amount
        FROM `tabSales Invoice Item` sii
        INNER JOIN `tabSales Invoice` si
            ON si.name = sii.parent
        WHERE
            si.docstatus = 1
            AND si.company = %(company)s
            AND sii.item_code = %(item_code)s
            {extra_customer_cond}
        ORDER BY si.posting_date DESC, sii.idx DESC
        LIMIT {limit}
        """.format(extra_customer_cond=extra_customer_cond, limit=limit),
        params,
        as_dict=True,
    )

    return {
        "count": len(rows),
        "rows": rows,
    }

@frappe.whitelist()
def get_ap_summary_by_supplier(company, supplier):
    """
    Ringkas hutang ke supplier: hanya outstanding_amount dari Purchase Invoice (docstatus=1).
    """
    res = frappe.db.get_all(
        "Purchase Invoice",
        filters={"docstatus": 1, "company": company, "supplier": supplier},
        fields=["sum(outstanding_amount) as outstanding"],
        limit_page_length=1,
    )
    outstanding_amount = flt((res[0].get("outstanding") if res else 0) or 0)
    return {
        "outstanding_amount": outstanding_amount
    }


@frappe.whitelist()
def get_ap_invoices_by_supplier(company, supplier):
    """
    AP details with credit-note application (Purchase):
      - invoices: Purchase Invoice (docstatus=1, outstanding>0) + adjusted_outstanding
                  setelah dikurangi Purchase Return (is_return=1) yang link (return_against) ke invoice tsb
      - credit_notes: sisa kredit dari Purchase Return yang belum habis terpakai
                      (termasuk return tanpa return_against -> berdiri sendiri)
      - advances: Payment Entry (Pay) unallocated_amount > 0 untuk supplier (pembayaran muka)
      - totals_extended: Net Payable = adjusted_outstanding - (credit_note_remaining + advances)
    Semua angka dalam mata uang company (pakai base_* / outstanding_amount PI).
    """

    company_currency = frappe.db.get_value("Company", company, "default_currency") or "IDR"

    # 1) Purchase Invoices dengan outstanding positif
    pi_rows = frappe.db.get_all(
        "Purchase Invoice",
        filters={"docstatus": 1, "company": company, "supplier": supplier, "outstanding_amount": [">", 0]},
        fields=["name", "posting_date", "base_grand_total", "outstanding_amount", "remarks"],
        order_by="posting_date desc",
        limit_page_length=500,
    )

    # 2) Purchase Returns (credit note) yang masih punya outstanding negatif (available credit)
    pr_rows = frappe.db.get_all(
        "Purchase Invoice",
        filters={"docstatus": 1, "company": company, "supplier": supplier, "is_return": 1, "outstanding_amount": ["<", 0]},
        fields=["name", "posting_date", "outstanding_amount", "return_against"],
        order_by="posting_date desc",
        limit_page_length=1000,
    )

    # Siapkan objek credit note & grouping per invoice asal
    cn_by_inv = {}   # {return_against: [cn_obj,...]}
    cn_objects = {}  # {cn_name: {"name":..., "posting_date":..., "available":..., "applied":0, "return_against":...}}
    for cn in pr_rows:
        available = flt(-cn.outstanding_amount)  # outstanding negatif -> available positif (kredit)
        obj = {
            "name": cn.name,
            "posting_date": cn.posting_date,
            "available": available,
            "applied": 0.0,
            "return_against": cn.return_against or None,
        }
        cn_objects[cn.name] = obj
        if cn.return_against:
            cn_by_inv.setdefault(cn.return_against, []).append(obj)

    # Terapkan kredit ke invoice asalnya
    invoices = []
    tot_gt = tot_paid = tot_out = 0.0
    total_applied_from_returns = 0.0

    # (opsional) urutkan CN per invoice asal
    for lst in cn_by_inv.values():
        lst.sort(key=lambda x: x["posting_date"], reverse=True)

    for inv in pi_rows:
        grand_total = flt(inv.base_grand_total)
        outstanding = flt(inv.outstanding_amount)
        paid_amount = flt(grand_total - outstanding)

        applied_credit = 0.0
        if inv.name in cn_by_inv:
            need = outstanding
            for cn in cn_by_inv[inv.name]:
                if need <= 0:
                    break
                avail = cn["available"] - cn["applied"]
                if avail <= 0:
                    continue
                use = min(avail, need)
                cn["applied"] += use
                applied_credit += use
                need -= use

        adjusted_outstanding = max(0.0, outstanding - applied_credit)
        total_applied_from_returns += applied_credit

        invoices.append({
            "name": inv.name,
            "posting_date": inv.posting_date,
            "grand_total": grand_total,
            "paid_amount": paid_amount,
            "outstanding_amount": outstanding,           # original
            "applied_credit": applied_credit,            # kredit return yang dipakai utk inv ini
            "adjusted_outstanding": adjusted_outstanding, # nilai yang dipakai di UI
            "remarks": getattr(inv, "remarks", "") or ""
        })

        tot_gt += grand_total
        tot_paid += paid_amount
        tot_out += outstanding

    # 3) Sisa credit note (remaining) per dokumen
    credit_notes_remaining = []
    total_credit_remaining = 0.0
    for cn in cn_objects.values():
        remaining = flt(cn["available"] - cn["applied"])
        if remaining > 0:
            credit_notes_remaining.append({
                "name": cn["name"],
                "posting_date": cn["posting_date"],
                "return_against": cn["return_against"],
                "available_amount": remaining,
            })
            total_credit_remaining += remaining

    # 4) Advances / Dana Menggantung (PE Pay unallocated)
    adv_rows = frappe.db.get_all(
        "Payment Entry",
        filters={
            "docstatus": 1,
            "company": company,
            "party_type": "Supplier",
            "party": supplier,
            "payment_type": "Pay",
            "unallocated_amount": [">", 0],
        },
        fields=["name", "posting_date", "unallocated_amount"],
        order_by="posting_date desc",
        limit_page_length=500,
    )
    advances = []
    total_unallocated = 0.0
    for r in adv_rows:
        amt = flt(r.unallocated_amount)
        advances.append({"name": r.name, "posting_date": r.posting_date, "unallocated_amount": amt})
        total_unallocated += amt

    # 5) Totals & Net Payable
    invoices_outstanding_adjusted = sum(flt(i["adjusted_outstanding"]) for i in invoices)
    net_payable = flt(invoices_outstanding_adjusted - total_credit_remaining - total_unallocated)

    return {
        "currency": company_currency,
        "invoices": invoices,
        "totals": {
            "grand_total": tot_gt,
            "paid_amount": tot_paid,
            "outstanding_amount": tot_out,  # original (belum dikurangi return)
            "applied_credit_from_returns": total_applied_from_returns,
        },
        "credit_notes": credit_notes_remaining,  # sisa kredit yang belum terpakai
        "advances": advances,
        "totals_adjusted": {
            "invoices_outstanding_adjusted": invoices_outstanding_adjusted
        },
        "totals_extended": {
            "invoices_outstanding_adjusted": invoices_outstanding_adjusted,
            "credit_note_available": total_credit_remaining,
            "advance_unallocated": total_unallocated,
            "net_payable": net_payable,
        },
    }

@frappe.whitelist()
def get_item_cost_history(company, item_code, supplier=None, limit=100):
    """
    Riwayat harga BELI item dari Purchase Invoice (docstatus=1, non-return).
    Kolom ramping: tanggal, no invoice, qty, uom, %disc, rate, net_amount.
    """
    try:
        limit = int(limit or 100)
    except Exception:
        limit = 100
    limit = min(max(limit, 1), 500)

    params = {
        "company": company,
        "item_code": item_code,
    }
    extra_supplier_cond = ""
    if supplier:
        extra_supplier_cond = " AND pi.supplier = %(supplier)s "
        params["supplier"] = supplier

    rows = frappe.db.sql(
        """
        SELECT
            pi.name         AS invoice,
            pi.posting_date AS posting_date,
            pii.item_code   AS item_code,
            pii.item_name   AS item_name,
            pii.qty         AS qty,
            pii.uom         AS uom,
            pii.discount_percentage,
            pii.rate,
            pii.net_amount
        FROM `tabPurchase Invoice Item` pii
        INNER JOIN `tabPurchase Invoice` pi
            ON pi.name = pii.parent
        WHERE
            pi.docstatus = 1
            AND pi.is_return = 0
            AND pi.company = %(company)s
            AND pii.item_code = %(item_code)s
            {extra_supplier_cond}
        ORDER BY pi.posting_date DESC, pii.idx DESC
        LIMIT {limit}
        """.format(extra_supplier_cond=extra_supplier_cond, limit=limit),
        params,
        as_dict=True,
    )

    return {
        "count": len(rows),
        "rows": rows,
    }

# tekma_app/utils.py
import frappe
from decimal import Decimal, ROUND_HALF_UP

def _compute_valuation_rates_core(finished_items, total_rm_cost, rounding=0):
    total_rm_cost = Decimal(total_rm_cost)
    total_ratio_units = Decimal(0)

    normalized = []
    for it in finished_items:
        qty = Decimal(it.get("qty") or 0)
        ratio = Decimal(it.get("ratio") or 1)
        if qty <= 0 or ratio <= 0:
            frappe.throw(f"Qty/Ratio harus > 0 untuk item {it.get('item_code')}")
        ru = qty * ratio
        total_ratio_units += ru
        normalized.append({**it, "qty": qty, "ratio": ratio, "ratio_units": ru})

    if total_ratio_units == 0:
        frappe.throw("Total ratio units = 0, tidak bisa membagi biaya")

    cost_per_ratio_unit = (total_rm_cost / total_ratio_units)
    quantize_str = "1" if rounding == 0 else f"1.{'0'*rounding}"

    result = {}
    for it in normalized:
        valuation_per_unit = (cost_per_ratio_unit * it["ratio"]).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        total_cost_for_item = (valuation_per_unit * it["qty"]).quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP)
        result[it["item_code"]] = {
            "qty": float(it["qty"]),
            "ratio": float(it["ratio"]),
            "valuation_rate": float(valuation_per_unit),
            "total_cost": float(total_cost_for_item),
        }

    sum_allocated = sum(v["total_cost"] for v in result.values())
    result["_meta"] = {
        "total_rm_cost": float(total_rm_cost),
        "sum_allocated": float(sum_allocated),
        "difference": float(total_rm_cost - Decimal(str(sum_allocated))),
    }
    return result


@frappe.whitelist()
def compute_valuation_rates(doc=None, rounding: int = 0):
    """
    Dipanggil dari client (Stock Entry).
    - Ambil RM (baris dengan s_warehouse terisi & t_warehouse kosong)
    - Ambil FG (baris dengan t_warehouse terisi & s_warehouse kosong)
    - Ambil 'ratio' dari child (gunakan field 'ratio' atau 'custom_ratio', default 1)
    - Hitung valuation_rate FG secara proporsional ratio × qty
    Return:
      { item_code: {qty, ratio, valuation_rate, total_cost}, _meta: {...} }
    """
    if not doc:
        frappe.throw("Parameter doc wajib diisi")
    doc = frappe.parse_json(doc)

    items = (doc.get("items") or [])
    # Raw Materials = keluar gudang (s_warehouse ada), bukan masuk (t_warehouse kosong)
    rm_rows = [d for d in items if d.get("s_warehouse") and not d.get("t_warehouse")]
    # Finished Goods = masuk gudang (t_warehouse ada), bukan keluar (s_warehouse kosong)
    fg_rows = [d for d in items if d.get("t_warehouse") and not d.get("s_warehouse")]

    if not rm_rows:
        frappe.throw("Tidak ditemukan baris Raw Material (baris dengan s_warehouse terisi).")
    if not fg_rows:
        frappe.throw("Tidak ditemukan baris Finished Goods (baris dengan t_warehouse terisi).")

    # Hitung total biaya RM (qty * basic_rate/valuation_rate)
    total_rm_cost = 0.0
    for r in rm_rows:
        qty = float(r.get("qty") or 0)
        rate = r.get("basic_rate")
        if rate in (None, "", 0):
            rate = r.get("valuation_rate") or 0
        total_rm_cost += qty * float(rate or 0)

    if total_rm_cost <= 0:
        frappe.throw("Total biaya Raw Material = 0. Pastikan basic_rate/valuation_rate RM terisi.")

    # Siapkan list FG dengan ratio
    finished_items = []
    for r in fg_rows:
        ratio = r.get("ratio", r.get("custom_ratio", 1))  # dukung custom field
        finished_items.append({
            "item_code": r.get("item_code"),
            "qty": r.get("qty"),
            "ratio": ratio,
        })

    return _compute_valuation_rates_core(
        finished_items=finished_items,
        total_rm_cost=total_rm_cost,
        rounding=int(rounding or 0),
    )
