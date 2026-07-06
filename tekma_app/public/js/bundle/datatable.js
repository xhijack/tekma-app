frappe.provide("frappe.views.QueryReport");

const datatable_state = {
    report_name: "",
    datatable: null,

    get key() {
        return `dt_state:${this.report_name}`;
    },

    get $filters() {
        if (!this.datatable) return $();
        return $(this.datatable.wrapper).find("input.dt-filter");
    },

    get cm() {
        return this.datatable?.columnmanager;
    },

    init(dt, name) {
        this.report_name = name;
        this.datatable = dt;

        this.bind_event();
        this.restore_sort();

        requestAnimationFrame(() => {
            this.restore_filters();
            this.update_filter_ui();
        });

        this.bind_datatable_events();
    },

    bind_event() {
        $(this.datatable.wrapper).on("input change", "input.dt-filter", () => {
            this.save_filters();
            this.apply_filters();
            this.update_filter_ui();
        });
    },

    bind_datatable_events() {
        this.datatable.on("onSortColumn", (e) => {
            this.save_sort(e.fieldname, e.sortOrder);

            requestAnimationFrame(() => {
                this.restore_filters();
                this.update_filter_ui();
            });
        });
    },

    save_filters() {
        localStorage.setItem(
            this.key + ":filters",
            JSON.stringify(this.get_filters())
        );
    },

    save_sort(fieldname, order) {
        localStorage.setItem(
            this.key + ":sort",
            JSON.stringify({ fieldname, order })
        );
    },

    get_filters() {
        let result = {};

        this.$filters.each((i, el) => {
            el = $(el);
            const key = el.data("name");

            if (key) {
                result[key] = el.val();
            }
        });

        return result;
    },

    restore_sort() {
        const state = JSON.parse(
            localStorage.getItem(this.key + ":sort") || "{}"
        );

        if (!state.fieldname || !state.order) return;

        const cols = this.datatable.getColumns();
        const index = cols.findIndex(c => c.fieldname === state.fieldname);

        if (index < 0) return;

        this.datatable.sortColumn(index, state.order);
    },

    restore_filters() {
        const state = JSON.parse(
            localStorage.getItem(this.key + ":filters") || "{}"
        );

        const cm = this.cm;
        if (!cm) return;

        const toFilters = {};

        this.$filters.each((i, el) => {
            el = $(el);

            const key = el.data("name");
            const colIndex = el.data("col-index");

            if (state?.[key] !== undefined) {
                el.val(state[key]);
                toFilters[colIndex] = state[key];
            }
        });

        requestAnimationFrame(() => {
            cm.applyFilter(toFilters);
        });
    },

    apply_filters() {
        const filters = this.get_filters();
        const toFilters = {};

        this.$filters.each((i, el) => {
            el = $(el);

            const colIndex = el.data("col-index");
            const key = el.data("name");

            if (filters?.[key] !== undefined) {
                toFilters[colIndex] = filters[key];
            }
        });

        this.cm.applyFilter(toFilters);
    },

    update_filter_ui() {
        const filters = this.get_filters();

        this.$filters.each((i, el) => {
            el = $(el);

            const key = el.data("name");

            if (key && filters[key]) {
                el.css({
                    "border": "1px solid #e74c3c",
                    "outline": "2px solid rgba(231, 76, 60, 0.35)",
                    "background-color": "rgba(231, 76, 60, 0.05)"
                });
            } else {
                el.css({
                    "border": "",
                    "outline": "",
                    "background-color": ""
                });
            }
        });
    }
};

frappe.views.QueryReport.prototype.render_datatable = function () {
    let data = this.data;
    let columns = this.columns.filter((col) => !col.hidden);

    if (data.length > (cint(frappe.boot.sysdefaults.max_report_rows) || 100000)) {
        let msg = __(
            "This report contains {0} rows and is too big to display in browser, you can {1} this report instead.",
            [cstr(format_number(data.length, null, 0)).bold(), __("export").bold()]
        );

        this.toggle_message(true, `${frappe.utils.icon("solid-warning")} ${msg}`);
        return;
    }

    if (this.raw_data.add_total_row && !this.report_settings.tree) {
        data = data.slice();
        data.splice(-1, 1);
    }

    this.$report.show();
    if (
        this.datatable &&
        this.datatable.options &&
        this.datatable.options.showTotalRow === this.raw_data.add_total_row
    ) {
        this.datatable.options.treeView = this.tree_report;
        this.datatable.refresh(data, columns);
    } else {
        let datatable_options = {
            columns: columns,
            data: data,
            inlineFilters: true,
            language: frappe.boot.lang,
            translations: frappe.utils.datatable.get_translations(),
            treeView: this.tree_report,
            layout: "fixed",
            cellHeight: 33,
            showTotalRow: this.raw_data.add_total_row && !this.report_settings.tree,
            direction: frappe.utils.is_rtl() ? "rtl" : "ltr",
            hooks: {
                columnTotal: frappe.utils.report_column_total,
            },
        };

        if (this.report_settings.get_datatable_options) {
            datatable_options = this.report_settings.get_datatable_options(datatable_options);
        }
        this.datatable = new window.DataTable(this.$report[0], datatable_options);
    }

    if (typeof this.report_settings.initial_depth == "number") {
        this.datatable.rowmanager.setTreeDepth(this.report_settings.initial_depth);
    }
    if (this.report_settings.after_datatable_render) {
        this.report_settings.after_datatable_render(this.datatable);
    }
    this.datatable_state = datatable_state.init(this.datatable, this.report_name);
}