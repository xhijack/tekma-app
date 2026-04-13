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

        pr_map = {}

        # ambil semua Purchase Receipt
        pr_names = list({
            d.get("voucher_no")
            for d in data
            if d.get("voucher_type") == "Purchase Receipt"
        })

        if pr_names:
            items = frappe.get_all(
                "Purchase Receipt Item",
                filters={"parent": ["in", pr_names]},
                fields=["parent", "item_code", "description"]
            )

            # mapping: (PR, item_code)
            for d in items:
                key = (d.parent, d.item_code)
                pr_map[key] = d.description

        # inject ke row
        for row in data:
            if row.get("voucher_type") == "Purchase Receipt":
                key = (row.get("voucher_no"), row.get("item_code"))
                row["description_item"] = pr_map.get(key)

        return columns, data

    stock_ledger.execute = custom_execute
    stock_ledger._patched = True