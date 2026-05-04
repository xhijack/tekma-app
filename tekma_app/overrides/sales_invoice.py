from erpnext.selling.doctype.delivery_note.delivery_note import make_sales_invoice as _make_si
import frappe

@frappe.whitelist()
def make_sales_invoice(source_name, target_doc=None):
    si = _make_si(source_name, target_doc)

    dn = frappe.get_doc("Delivery Note", source_name)

    if dn.remarks:
        si.remarks = dn.remarks

    return si