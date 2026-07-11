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


const FULL_WIDTH_FIELD_TYPES = new Set([
	"Text",
	"Small Text",
	"Long Text",
	"Text Editor",
	"Code",
	"Markdown Editor",
	"Attach",
	"Attach Image",
	"Image",
]);

const HIDDEN_FIELD_TYPES = new Set([
	"Section Break",
	"Column Break",
	"Tab Break",
	"Fold",
	"Heading",
	"HTML",
	"Button",
	"Table",
	"Table MultiSelect",
]);


export default class MobileGridRow extends GridRow {
	make() {
		this.wrapper = $('<div class="grid-row mobile-grid-row"></div>');

		this.row = $(`
			<div
				class="mobile-grid-card"
				role="button"
				tabindex="0"
			></div>
		`).appendTo(this.wrapper);

		this.render_row();

		this.set_data();
		this.wrapper.appendTo(this.parent);
	}

	render_row() {
		if (this.header_row || this.show_search) {
			return false;
		}

		this.row.empty();

		this.render_card_header();
		this.render_card_body();
		this.set_row_index();
		this.refresh_check();

		if (this.frm && this.doc) {
			$(this.frm.wrapper).trigger(
				"grid-row-render",
				[this]
			);
		}

		return true;
	}

	render_card_header() {
		const editable = Boolean(
			this.grid?.is_editable()
		);

		const can_delete =
			editable &&
			!this.grid.df?.cannot_delete_rows;

		const $header = $(`
			<div class="mobile-grid-card-header">
				<div class="mobile-grid-card-index">
					<label class="mobile-grid-check-wrapper">
						<input
							type="checkbox"
							class="grid-row-check"
							tabindex="-1"
						>
					</label>

					<span class="mobile-grid-row-title">
						${__("Row")} #${frappe.utils.escape_html(
							String(this.doc?.idx || "")
						)}
					</span>
				</div>

				<div class="mobile-grid-card-actions">
					<button
						type="button"
						class="btn btn-xs btn-secondary mobile-grid-edit"
					>
						${frappe.utils.icon("edit", "xs")}
						<span>
							${editable ? __("Edit") : __("View")}
						</span>
					</button>

					${
						can_delete
							? `
								<button
									type="button"
									class="btn btn-xs btn-danger mobile-grid-delete"
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

		this.row_index = $header.find(
			".mobile-grid-row-title"
		);

		this.row_check
			.prop("checked", Boolean(this.doc?.__checked))
			.on("click", (event) => {
				event.stopPropagation();
			})
			.on("change", (event) => {
				event.stopPropagation();

				const checked = $(event.currentTarget).prop(
					"checked"
				);

				this.select(checked);

				this.row.toggleClass(
					"mobile-grid-card-selected",
					checked
				);

				this.grid.refresh_remove_rows_button();
			});

		$header
			.find(".mobile-grid-edit")
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
					__(
						"Are you sure you want to delete this row?"
					),
					() => {
						this.remove();
					}
				);

				return false;
			});

		this.row
			.off("click.mobile-grid")
			.on("click.mobile-grid", (event) => {
				if (
					$(event.target).closest(
						[
							"input",
							"button",
							"a",
							"select",
							"textarea",
						].join(",")
					).length
				) {
					return;
				}

				event.preventDefault();
				event.stopPropagation();

				this.toggle_view(true);

				return false;
			});

		this.row
			.off("keydown.mobile-grid")
			.on("keydown.mobile-grid", (event) => {
				if (
					event.key !== "Enter" &&
					event.key !== " "
				) {
					return;
				}

				if (
					$(event.target).is(
						"input, button, a, select, textarea"
					)
				) {
					return;
				}

				event.preventDefault();
				event.stopPropagation();

				this.toggle_view(true);
			});
	}

	render_card_body() {
		const $body = $(
			'<div class="mobile-grid-card-body"></div>'
		).appendTo(this.row);

		const fields = this.get_mobile_fields();

		if (!fields.length) {
			$body.append(`
				<div class="mobile-grid-no-fields">
					${__("No visible fields")}
				</div>
			`);

			return;
		}

		fields.forEach((df) => {
			$body.append(
				this.make_mobile_field(df)
			);
		});
	}

	get_mobile_fields() {
		const docfields =
			this.docfields ||
			this.grid.docfields ||
			[];

		const selected_fields =
			this.grid.user_defined_columns?.length
				? this.grid.user_defined_columns
				: docfields;

		const fields = [];
		const included = new Set();

		this.grid.setup_visible_columns();

		for (
			const visible_column of
			this.grid.visible_columns || []
		) {
			const visible_df = visible_column?.[0];

			if (!visible_df?.fieldname) {
				continue;
			}

			const df =
				selected_fields.find(
					(field) =>
						field?.fieldname ===
						visible_df.fieldname
				) ||
				docfields.find(
					(field) =>
						field?.fieldname ===
						visible_df.fieldname
				) ||
				visible_df;

			if (!this.should_show_mobile_field(df)) {
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
				if (!this.should_show_mobile_field(df)) {
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

	should_show_mobile_field(df) {
		if (!df?.fieldname) {
			return false;
		}

		if (HIDDEN_FIELD_TYPES.has(df.fieldtype)) {
			return false;
		}

		if (
			frappe.model.no_value_type.includes(
				df.fieldtype
			)
		) {
			return false;
		}

		if (df.hidden) {
			return false;
		}

		try {
			this.set_dependant_property(df);
		} catch (error) {
			console.warn(
				`Cannot evaluate dependency for ${df.fieldname}`,
				error
			);
		}

		return !df.hidden_due_to_dependency;
	}

	make_mobile_field(df) {
		const raw_value = this.doc?.[df.fieldname];
		const formatted_value = this.format_mobile_value(
			df,
			raw_value
		);

		const full_width =
			FULL_WIDTH_FIELD_TYPES.has(df.fieldtype) ||
			cint(df.columns) >= 6 ||
			cint(df.colsize) >= 6;

		const required_empty =
			df.reqd &&
			this.is_empty_mobile_value(
				raw_value,
				df
			);

		const $field = $(`
			<div
				class="
					mobile-grid-card-field
					${full_width ? "mobile-grid-card-field-full" : ""}
					${required_empty ? "mobile-grid-card-field-required" : ""}
					${df.bold ? "mobile-grid-card-field-bold" : ""}
				"
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

				<div class="mobile-grid-card-field-value">
					${
						formatted_value ||
						'<span class="mobile-grid-empty-value">—</span>'
					}
				</div>
			</div>
		`);

		return $field;
	}

	format_mobile_value(df, value) {
		if (df.fieldtype === "Check") {
			return value
				? frappe.utils.icon("check", "sm")
				: frappe.utils.icon("close", "sm");
		}

		if (df.fieldtype === "Select") {
			return frappe.utils.escape_html(
				value ? __(String(value)) : ""
			);
		}

		if (
			[
				"Text",
				"Small Text",
				"Long Text",
				"Code",
			].includes(df.fieldtype)
		) {
			return frappe.utils
				.escape_html(String(value ?? ""))
				.replace(/\n/g, "<br>");
		}

		try {
			const formatted = frappe.format(
				value,
				df,
				null,
				this.doc
			);

			return formatted == null
				? ""
				: String(formatted);
		} catch (error) {
			return frappe.utils.escape_html(
				String(value ?? "")
			);
		}
	}

	is_empty_mobile_value(value, df) {
		if (df.fieldtype === "Check") {
			return false;
		}

		return (
			value === undefined ||
			value === null ||
			value === ""
		);
	}

	refresh() {
		if (this.frm && this.doc) {
			this.doc =
				locals[this.doc.doctype]?.[this.doc.name] ||
				this.doc;
		}

		this.render_row();

		if (this.grid_form) {
			this.grid_form.layout?.refresh(this.doc);
		}
	}

	refresh_field(fieldname) {
		const df = this.docfields?.find(
			(field) => field.fieldname === fieldname
		);

		if (!df) {
			return;
		}

		const $existing = this.row.find(
			`.mobile-grid-card-field[data-fieldname="${fieldname}"]`
		);

		if (!$existing.length) {
			this.render_row();
			return;
		}

		const $replacement = this.make_mobile_field(df);

		$existing.replaceWith($replacement);

		if (this.grid_form) {
			this.grid_form.refresh_field(fieldname);
		}
	}

	refresh_check() {
		const checked = Boolean(
			this.doc?.__checked
		);

		this.row_check?.prop("checked", checked);

		this.row.toggleClass(
			"mobile-grid-card-selected",
			checked
		);

		this.grid.refresh_remove_rows_button();
	}
}