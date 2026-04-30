import frappe

def patch():
    from erpnext.stock.report.stock_ledger import stock_ledger

    if getattr(stock_ledger, "_patched", False):
        return

    original_execute = stock_ledger.execute

    def custom_execute(filters=None):
        columns, data = original_execute(filters)

        # tambah kolom
        columns.append({
            "label": "Description Item",
            "fieldname": "description_item",
            "fieldtype": "Data",
            "width": 250
        })

        # mapping doctype -> item table
        doctype_map = {
            "Purchase Receipt": "Purchase Receipt Item",
            "Purchase Invoice": "Purchase Invoice Item",
            "Delivery Note": "Delivery Note Item",
            "Sales Invoice": "Sales Invoice Item",
            "Stock Entry": "Stock Entry Detail",
            # "Stock Reconciliation": "Stock Reconciliation Item",
        }

        # kumpulkan voucher per type
        voucher_map = {}
        for row in data:
            vt = row.get("voucher_type")
            vn = row.get("voucher_no")

            if vt in doctype_map and vn:
                voucher_map.setdefault(vt, set()).add(vn)

        # ambil semua data sekaligus
        description_map = {}

        for vt, vouchers in voucher_map.items():
            item_doctype = doctype_map[vt]

            items = frappe.get_all(
                item_doctype,
                filters={"parent": ["in", list(vouchers)]},
                fields=["parent", "item_code", "description"]
            )

            for d in items:
                key = (vt, d.parent, d.item_code)
                description_map[key] = d.description

        # inject ke report
        for row in data:
            vt = row.get("voucher_type")
            vn = row.get("voucher_no")
            ic = row.get("item_code")

            key = (vt, vn, ic)
            row["description_item"] = description_map.get(key)

        return columns, data

    stock_ledger.execute = custom_execute
    stock_ledger._patched = True