let cached_mobile_device;

export function is_mobile_device() {
	if (cached_mobile_device !== undefined) {
		return cached_mobile_device;
	}

	if (typeof navigator === "undefined") {
		cached_mobile_device = false;
		return cached_mobile_device;
	}

	if (typeof navigator.userAgentData?.mobile === "boolean") {
		cached_mobile_device = navigator.userAgentData.mobile;
		return cached_mobile_device;
	}

	const user_agent =
		navigator.userAgent ||
		navigator.vendor ||
		"";

	const mobile_phone =
		/Android.*Mobile|iPhone|iPod|webOS|BlackBerry|IEMobile|Opera Mini|Windows Phone/i.test(
			user_agent
		);

	const android_tablet =
		/Android/i.test(user_agent) &&
		!/Mobile/i.test(user_agent);

	const ipad =
		/iPad/i.test(user_agent) ||
		(
			navigator.platform === "MacIntel" &&
			navigator.maxTouchPoints > 1
		);

	cached_mobile_device =
		mobile_phone ||
		android_tablet ||
		ipad;

	return cached_mobile_device;
}

import GridRow from "./grid_row";
import GridRowForm from "./grid_row_form";


const INLINE_FIELD_TYPES = new Set([
	"Data",
	"Link",
	"Dynamic Link",
	"Select",
	"Int",
	"Float",
	"Currency",
	"Percent",
	"Check",
	"Date",
	"Datetime",
	"Time",
	"Duration",
	"Small Text",
	"Long Text",
	"Text",
	"Phone",
	"Password",
	"Rating",
	"Barcode",
	"Color",
	"Geolocation",
]);

const STATIC_FIELD_TYPES = new Set([
	"Attach",
	"Attach Image",
	"Image",
	"Code",
	"Text Editor",
	"Markdown Editor",
	"Read Only",
]);

const HIDDEN_FIELD_TYPES = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"Fold",
	"Heading",
	"HTML",
	"HTML Editor",
	"Button",
	"Table",
	"Table MultiSelect",
]);

export default class MobileGridRow extends GridRow {
	make() {
		this.columns = {};
		this.columns_list = [];
		this.on_grid_fields = [];
		this.on_grid_fields_dict = {};
		this.mobile_fields_signature = null;

		this.wrapper = $('<div class="grid-row mobile-grid-row"></div>');

		this.row = $(
			'<div class="mobile-grid-card editable-row"></div>'
		).appendTo(this.wrapper);

		this.set_data();
		this.wrapper.appendTo(this.parent);

		this.render_row();
	}

	render_row() {
		if (!this.doc || this.header_row || this.show_search) {
			return false;
		}

		this.reload_doc();
		this.set_row_index();

		this.row.empty();

		this.columns = {};
		this.columns_list = [];
		this.on_grid_fields = [];
		this.on_grid_fields_dict = {};

		this.render_card_header();
		this.render_card_body();
		this.refresh_check();

		this.mobile_fields_signature = this.get_fields_signature();

		if (this.frm && this.doc) {
			$(this.frm.wrapper).trigger("grid-row-render", [this]);
		}

		return true;
	}

	reload_doc() {
		if (!this.frm || !this.doc) {
			return;
		}

		this.doc =
			locals[this.doc.doctype]?.[this.doc.name] ||
			this.doc;
	}

	render_card_header() {
		const editable = this.grid.is_editable();

		const can_delete =
			editable &&
			!this.grid.df?.cannot_delete_rows;

		const $header = $(`
			<div class="mobile-grid-card-header sortable-handle">
				<div class="mobile-grid-card-index">
					<label class="mobile-grid-check-wrapper">
						<input
							type="checkbox"
							class="grid-row-check"
							tabindex="-1"
						>
					</label>

					<span class="mobile-grid-row-title">
						${__("Row")}
						#<span class="mobile-grid-row-index">
							${frappe.utils.escape_html(
								String(this.doc.idx || "")
							)}
						</span>
					</span>
				</div>

				<div class="mobile-grid-card-actions">
					<button
						type="button"
						class="btn btn-xs btn-secondary mobile-grid-full-edit"
						title="${__("Edit Full Form")}"
						aria-label="${__("Edit Full Form")}"
					>
						${editable? frappe.utils.icon("edit", "xs"): frappe.utils.icon("view", "xs")}
					</button>

					${
						can_delete
							? `
								<button
									type="button"
									class="btn btn-xs btn-danger mobile-grid-delete"
									title="${__("Delete Row")}"
									aria-label="${__("Delete Row")}"
								>
									${frappe.utils.icon("delete", "xs")}
								</button>
							`
							: ""
					}
				</div>
			</div>
		`).appendTo(this.row);

		this.row_check = $header.find(".grid-row-check");
		this.row_index = $header.find(".mobile-grid-row-index");

		this.row_check
			.prop("checked", Boolean(this.doc.__checked))
			.on("click", (event) => {
				event.stopPropagation();
			});

		$header
			.find(".mobile-grid-full-edit")
			.on("click", (event) => {
				event.preventDefault();
				event.stopPropagation();

				this.toggle_view(true);

				return false;
			});

		$header
			.find(".mobile-grid-delete")
			.on("click", (event) => {
				event.preventDefault();
				event.stopPropagation();

				frappe.confirm(
					__("Are you sure you want to delete this row?"),
					() => {
						this.remove();
					}
				);

				return false;
			});
	}

	render_card_body() {
		this.body = $(
			'<div class="mobile-grid-card-body"></div>'
		).appendTo(this.row);

		const fields = this.get_mobile_fields();

		if (!fields.length) {
			this.body.append(`
				<div class="mobile-grid-no-fields text-muted">
					${__("No visible fields")}
				</div>
			`);

			return;
		}

		fields.forEach((df, index) => {
			this.render_mobile_field(df, index);
		});
	}

	get_mobile_fields() {
		const docfields =
			this.docfields ||
			this.grid.docfields ||
			[];

		const fields_by_name = new Map(
			docfields
				.filter((df) => df?.fieldname)
				.map((df) => [
					df.fieldname,
					df,
				])
		);

		const fields = [];
		const included = new Set();

		this.grid.setup_visible_columns();

		for (const visible_column of this.grid.visible_columns || []) {
			const visible_df = visible_column?.[0];

			if (!visible_df?.fieldname) {
				continue;
			}

			const df =
				fields_by_name.get(visible_df.fieldname) ||
				visible_df;

			if (!this.should_show_field(df)) {
				continue;
			}

			if (included.has(df.fieldname)) {
				continue;
			}

			included.add(df.fieldname);
			fields.push(df);
		}

		if (!fields.length) {
			for (const df of docfields) {
				if (!this.should_show_field(df)) {
					continue;
				}

				if (included.has(df.fieldname)) {
					continue;
				}

				included.add(df.fieldname);
				fields.push(df);
			}
		}

		return fields;
	}

	get_visible_columns() {
		return this.get_mobile_fields();
	}

	should_show_field(df) {
		if (!df?.fieldname) {
			return false;
		}

		if (HIDDEN_FIELD_TYPES.has(df.fieldtype)) {
			return false;
		}

		if (frappe.model.no_value_type.includes(df.fieldtype)) {
			return false;
		}

		if (df.hidden) {
			return false;
		}

		try {
			this.set_dependant_property(df);
		} catch (error) {
			console.warn(
				`Unable to evaluate dependency for ${df.fieldname}`,
				error
			);
		}

		return !df.hidden_due_to_dependency;
	}

	render_mobile_field(df, index) {
		const $column = $(`
			<div
				class="mobile-grid-card-field"
				data-fieldname="${frappe.utils.escape_html(
					df.fieldname
				)}"
				data-fieldtype="${frappe.utils.escape_html(
					df.fieldtype || ""
				)}"
			>
				<div class="mobile-grid-card-field-label">
					${frappe.utils.escape_html(
						__(
							df.label || df.fieldname,
							null,
							df.parent
						)
					)}

					${
						df.reqd
							? '<span class="text-danger">*</span>'
							: ""
					}
				</div>

				<div class="mobile-grid-card-field-control"></div>
			</div>
		`).appendTo(this.body);

		const column = {
			df,
			column_index: index,
			wrapper: $column,
			field_area: $column.find(
				".mobile-grid-card-field-control"
			),
			static_area: null,
			field: null,
		};

		column.static_area = column.field_area;

		this.columns[df.fieldname] = column;
		this.columns_list.push(column);

		const editable =
			this.grid.is_editable() &&
			!df.read_only &&
			!df.hidden_due_to_dependency &&
			INLINE_FIELD_TYPES.has(df.fieldtype);

		if (editable) {
			this.make_mobile_control(column, index);
		} else {
			this.render_static_field(column.field_area, df);
		}

		this.update_required_state(column, df);
	}

	make_mobile_control(column, index) {
		const df = column.df;

		const control_df = {
			...df,
		};

		const field = frappe.ui.form.make_control({
			df: control_df,
			parent: column.field_area,
			only_input: true,
			with_link_btn: true,
			render_input: true,
			doc: this.doc,
			doctype: this.doc.doctype,
			docname: this.doc.name,
			frm: this.frm,
			grid: this.grid,
			grid_row: this,
			value: this.doc[df.fieldname],
		});

		field.doc = this.doc;
		field.doctype = this.doc.doctype;
		field.docname = this.doc.name;
		field.frm = this.frm;
		field.grid = this.grid;
		field.grid_row = this;

		this.apply_field_info(field, df);

		const original_change = field.df.change;
		const original_onchange = field.df.onchange;

		field.df.change = (event) => {
			const value = field.get_value();

			const promise = frappe.model.set_value(
				this.doc.doctype,
				this.doc.name,
				df.fieldname,
				value
			);

			Promise.resolve(promise).then(() => {
				this.reload_doc();
				this.update_required_state(column, df);
				this.refresh_mobile_dependencies();
			});

			if (typeof original_change === "function") {
				original_change.call(field, event);
			} else if (typeof original_onchange === "function") {
				original_onchange.call(field, event);
			}
		};

		field.refresh();

		if (typeof field.set_value === "function") {
			field.set_value(this.doc[df.fieldname]);
		}

		field.refresh();

		column.field = field;

		this.on_grid_fields_dict[df.fieldname] = field;
		this.on_grid_fields.push(field);

		this.decorate_control(field, df, index);
	}

	apply_field_info(field, df) {
		const field_info =
			this.grid.get_field?.(df.fieldname) ||
			this.grid.fieldinfo?.[df.fieldname];

		if (!field_info) {
			return;
		}

		$.extend(field, field_info);

		if (field_info.get_query) {
			field.get_query = field_info.get_query;
		}
	}

	decorate_control(field, df, index) {
		field.$wrapper?.addClass(
			"mobile-grid-control-wrapper"
		);

		if (!field.$input) {
			return;
		}

		field.$input
			.addClass("mobile-grid-input input-sm")
			.attr("data-fieldname", df.fieldname)
			.attr("data-fieldtype", df.fieldtype);

		if (df.placeholder || df.label) {
			field.$input.attr(
				"placeholder",
				__(
					df.placeholder ||
						df.label ||
						""
				)
			);
		}

		if (index === 0) {
			field.$input.attr("data-first-input", "1");
		}
	}

	render_static_field($parent, df) {
		const value = this.doc?.[df.fieldname];

		let formatted = "";

		if (df.fieldtype === "Check") {
			formatted = value
				? frappe.utils.icon("check", "sm")
				: frappe.utils.icon("close", "sm");
		} else {
			try {
				formatted = frappe.format(
					value,
					df,
					null,
					this.doc
				);
			} catch (error) {
				formatted = frappe.utils.escape_html(
					String(value ?? "")
				);
			}
		}

		$parent
			.addClass("mobile-grid-static-control")
			.html(
				formatted ||
					'<span class="mobile-grid-empty-value">—</span>'
			);

		if (STATIC_FIELD_TYPES.has(df.fieldtype)) {
			$parent.addClass(
				"mobile-grid-complex-static"
			);
		}
	}

	update_required_state(column, df) {
		const value = this.doc?.[df.fieldname];

		const is_empty =
			value === undefined ||
			value === null ||
			value === "";

		column.wrapper.toggleClass(
			"mobile-grid-card-field-required",
			Boolean(
				df.reqd &&
					df.fieldtype !== "Check" &&
					is_empty
			)
		);
	}

	refresh() {
		this.reload_doc();
		this.set_row_index();

		const next_signature = this.get_fields_signature();

		if (
			!this.mobile_fields_signature ||
			this.mobile_fields_signature !== next_signature
		) {
			this.render_row();
			return;
		}

		this.refresh_controls();
		this.refresh_check();

		this.row_index?.text(this.doc.idx || "");
	}

	refresh_controls() {
		for (const column of this.columns_list) {
			const df = column.df;

			if (!df?.fieldname) {
				continue;
			}

			this.set_dependant_property(df);

			if (
				df.hidden ||
				df.hidden_due_to_dependency
			) {
				this.render_row();
				return;
			}

			const should_be_editable =
				this.grid.is_editable() &&
				!df.read_only &&
				INLINE_FIELD_TYPES.has(df.fieldtype);

			if (
				should_be_editable !==
				Boolean(column.field)
			) {
				this.render_row();
				return;
			}

			if (column.field) {
				column.field.doc = this.doc;
				column.field.doctype = this.doc.doctype;
				column.field.docname = this.doc.name;

				column.field.refresh();
			} else {
				column.field_area.empty();

				this.render_static_field(
					column.field_area,
					df
				);
			}

			this.update_required_state(column, df);
		}
	}

	refresh_field(fieldname) {
		this.reload_doc();

		const column = this.columns[fieldname];

		if (!column) {
			this.render_row();
			return;
		}

		const df = column.df;

		if (!df) {
			return;
		}

		const previous_state = JSON.stringify([
			Boolean(df.hidden),
			Boolean(df.hidden_due_to_dependency),
			Boolean(df.read_only),
			Boolean(df.reqd),
		]);

		this.set_dependant_property(df);

		const next_state = JSON.stringify([
			Boolean(df.hidden),
			Boolean(df.hidden_due_to_dependency),
			Boolean(df.read_only),
			Boolean(df.reqd),
		]);

		if (previous_state !== next_state) {
			this.render_row();
			return;
		}

		const should_be_editable =
			this.grid.is_editable() &&
			!df.read_only &&
			!df.hidden_due_to_dependency &&
			INLINE_FIELD_TYPES.has(df.fieldtype);

		if (
			should_be_editable !==
				Boolean(column.field)
		) {
			this.render_row();
			return;
		}

		if (column.field) {
			column.field.doc = this.doc;
			column.field.doctype = this.doc.doctype;
			column.field.docname = this.doc.name;

			column.field.refresh();
		} else {
			column.field_area.empty();

			this.render_static_field(
				column.field_area,
				df
			);
		}

		this.update_required_state(column, df);

		if (this.grid_form) {
			this.grid_form.refresh_field(fieldname);
		}

		this.refresh_mobile_dependencies();
	}

	refresh_mobile_dependencies() {
		const previous_signature =
			this.mobile_fields_signature;

		for (const df of this.docfields || []) {
			if (
				!df.depends_on &&
				!df.mandatory_depends_on &&
				!df.read_only_depends_on
			) {
				continue;
			}

			this.set_dependant_property(df);
		}

		const next_signature = this.get_fields_signature();

		if (previous_signature !== next_signature) {
			this.render_row();
			return;
		}

		this.mobile_fields_signature = next_signature;
	}

	get_fields_signature() {
		return JSON.stringify(
			this.get_mobile_fields().map((df) => [
				df.fieldname,
				df.fieldtype,
				Boolean(df.hidden),
				Boolean(df.hidden_due_to_dependency),
				Boolean(df.read_only),
				Boolean(df.reqd),
				Boolean(this.grid.is_editable()),
			])
		);
	}

	refresh_check() {
		const checked = Boolean(this.doc?.__checked);

		this.row_check?.prop("checked", checked);

		this.row.toggleClass(
			"mobile-grid-card-selected",
			checked
		);

		this.grid.refresh_remove_rows_button();
	}

	make_editable() {
		this.row.toggleClass(
			"editable-row",
			this.grid.is_editable()
		);
	}

	toggle_editable_row() {
		this.focus_first_input();
		return this;
	}

	activate() {
		this.focus_first_input();
		return this;
	}

	focus_first_input() {
		const $input = this.row
			.find(
				[
					"input:enabled:not([type='hidden']):not([type='checkbox'])",
					"select:enabled",
					"textarea:enabled",
				].join(",")
			)
			.first();

		if (!$input.length) {
			return;
		}

		try {
			$input.get(0).focus({
				preventScroll: true,
			});
		} catch (error) {
			$input.get(0).focus();
		}
	}

	set_arrow_keys() {
		// Navigasi keyboard desktop tidak digunakan pada card mobile.
	}
}