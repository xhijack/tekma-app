// TODO: revisit and properly implement this client script
frappe.pages["print"].on_page_load = function (wrapper) {
	frappe.ui.make_app_page({
		parent: wrapper,
	});
	let print_view = new frappe.ui.form.PrintView(wrapper);
};
frappe.ui.form.PrintView = class PrintView extends frappe.ui.form.PrintView {
	constructor(wrapper) {
		super(wrapper);
	}
    init_receiptline(){
        return new Promise((resolve) => {
            if (typeof receiptline === "object") {
                resolve();
            } else {
                let receiptline_required_assets = [
                    "/assets/tekma_app/node_modules/receiptline/lib/receiptline.js",
                    
                ];
                frappe.require(receiptline_required_assets, () => {
                    resolve();
                });
                // note 'frappe.require' does not have callback on fail. Hence, any failure cannot be communicated to the user.
            }
        });
    }
    make_receiptline(markdown){
        return new Promise((resolve, reject) => {
            this.init_receiptline().then(() => {
                try{
                    let command = receiptline.transform(markdown, {command: "epson", cpl: 48, spacing: true, encoding: "multilingual", gamma: 8})
                    console.log(command)
                    resolve(command)
                }catch(e){
                    reject(e)
                }
            })
        })
    }
	make() {
		super.make();
	}
	printit() {
		let me = this;

		if (cint(me.print_settings.enable_print_server)) {
			if (localStorage.getItem("network_printer")) {
				me.print_by_server();
			} else {
				me.network_printer_setting_dialog(() => me.print_by_server());
			}
		} else if (me.get_mapped_printer().length === 1) {
			// printer is already mapped in localstorage (applies for both raw and pdf )
			if (me.is_raw_printing()) {
				me.get_raw_commands(function (out) {
					frappe.ui.form
						.qz_connect()
						.then(function () {
							let printer_map = me.get_mapped_printer()[0];
                            return me.make_receiptline(out.raw_commands).then((command) => {
                                let data = [{ type: 'raw', format: 'command', flavor: 'base64', data: btoa(command)}];
                                let config = qz.configs.create(printer_map.printer);
                                return qz.print(config, data);
                            })
						})
						.then(frappe.ui.form.qz_success)
						.catch((err) => {
							frappe.ui.form.qz_fail(err);
						});
				});
			} else {
				frappe.show_alert(
					{
						message: __('PDF printing via "Raw Print" is not supported.'),
						subtitle: __(
							"Please remove the printer mapping in Printer Settings and try again."
						),
						indicator: "info",
					},
					14
				);
				//Note: need to solve "Error: Cannot parse (FILE)<URL> as a PDF file" to enable qz pdf printing.
			}
		} else if (me.is_raw_printing()) {
			// printer not mapped in localstorage and the current print format is raw printing
			frappe.show_alert(
				{
					message: __("Printer mapping not set."),
					subtitle: __(
						"Please set a printer mapping for this print format in the Printer Settings"
					),
					indicator: "warning",
				},
				14
			);
			me.printer_setting_dialog();
		} else {
			me.render_page("/printview?", true);
		}
	}
};