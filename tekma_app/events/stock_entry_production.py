import frappe
from frappe.utils import flt
# Handle stock entry prduksi untuk menandai refrensi dokumen sudah digunakan
def on_submit_stock_entry_production(doc, method):
    _validate_value_balance(doc)
    update_is_open(doc, 0)

def on_cancel_stock_entry_production(doc, method):
    update_is_open(doc, 1)


def update_is_open(doc, is_open = 1):
    if doc.stock_entry_type in ["Mincer", "Mixer", "Wrap"] and doc.prod_reference:
        frappe.db.set_value("Stock Entry", doc.prod_reference, "is_open", is_open, update_modified=False)


_EXCLUDED_FROM_BALANCE_CHECK = {"Material Receipt", "Material Issue"}

def _validate_value_balance(doc):
    if doc.purpose in _EXCLUDED_FROM_BALANCE_CHECK:
        return
    diff = flt(doc.value_difference or 0)
    
    if not(-10 < abs(diff) < 10):
        frappe.throw(
            f"Stock Entry tipe <b>{doc.stock_entry_type}</b> harus balance "
            f"(nilai masuk = nilai keluar). Selisih saat ini: <b>{diff}</b>. "
            "Pastikan semua baris sudah terisi basic_rate/valuation_rate dengan benar."
        )


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