# Copyright (c) 2025, PT Sopwer Teknologi Indonesia and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import db


class DailyProduction(Document):
	def validate(self):
		for item in self.productions:
			item.qty_sales_order = self.get_qty_so_to_deliver(item.item_code)
			item.actual_qty = self.get_actul_qty_based_on_item_code_and_warehouse(item.item_code, self.warehouse)
			# item.prediction_qty = item.actual_qty + item.qty_sales_order + item.qty_production
			item.prediction_qty = item.actual_qty + item.qty_production - item.qty_sales_order
			item.sum_kg = self.calculate_ratio_item_with_prediction_qty(item.item_code, item.prediction_qty)

	def get_qty_based_on_sales_order_undelivered(self, item_code):
		sales_orders = db.get_all(
			"Sales Order",
			fields=["name"],
			filters={
				"docstatus": 1,
				"status": ["not in", ["Closed", "Completed"]],
			}
	 )

		total_qty = 0
		for so in sales_orders:
			items = db.get_all(
				"Sales Order Item",
				fields=["qty", "delivered_qty"],
				filters={
					"parent": so["name"],
					"item_code": item_code
				}
			)
			for item in items:
				undelivered_qty = item["qty"] - item.get("delivered_qty", 0)
				if undelivered_qty > 0:
					total_qty += undelivered_qty

		return total_qty

	# Update Function
	def get_qty_so_to_deliver(self, item_code):
		sales_orders = db.get_all(
			"Sales Order",
			fields=["name"],
			filters={
				"docstatus": 1,
				"status": "To Deliver and Bill",
			}
		)

		total_qty = 0
		for so in sales_orders:
			items = db.get_all(
				"Sales Order Item",
				fields=["qty", "delivered_qty"],
				filters={
					"parent": so["name"],
					"item_code": item_code
				}
			)
			for item in items:
				undelivered_qty = (item.qty or 0) - (item.delivered_qty or 0)
				if undelivered_qty > 0:
					total_qty += undelivered_qty
		
		return total_qty

	def get_actul_qty_based_on_item_code_and_warehouse(self, item_code, warehouse):
		actual_qty = db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
		return actual_qty or 0

	def calculate_ratio_item_with_prediction_qty(self, item_code, prediction_qty):
		item = frappe.get_doc("Item", item_code)
		if item.ratio == 0:
			frappe.throw
		return item.ratio * prediction_qty if item.ratio else 0

@frappe.whitelist()
def get_qty_info(item_code, warehouse):
    # qty_sales_order
    sales_orders = frappe.get_all(
        "Sales Order",
        filters={"docstatus": 1, "status": "To Deliver and Bill"},
        fields=["name"]
    )
    total_qty = 0
    for so in sales_orders:
        items = frappe.get_all(
            "Sales Order Item",
            filters={"parent": so.name, "item_code": item_code},
            fields=["qty", "delivered_qty"]
        )
        for item in items:
            undelivered_qty = (item.qty or 0) - (item.delivered_qty or 0)
            if undelivered_qty > 0:
                total_qty += undelivered_qty
    qty_sales_order = total_qty

    # actual_qty
    actual_qty = frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty") or 0

    # prediction_qty
    prediction_qty = actual_qty - qty_sales_order

    # sum_kg
    item_doc = frappe.get_doc("Item", item_code)
    ratio = item_doc.ratio or 0
    sum_kg = item_doc.ratio * prediction_qty if item_doc.ratio else 0

    return {
        "qty_sales_order": qty_sales_order,
        "actual_qty": actual_qty,
        "prediction_qty": prediction_qty,
        "sum_kg": sum_kg,
        "ratio": ratio
    }
