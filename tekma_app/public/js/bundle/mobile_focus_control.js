import { is_mobile_device } from './mobile_device'
frappe.provide("frappe.ui");

frappe.ui.form.Layout.prototype.setup_events = function () {
	let last_scroll = 0;
	let keyboard_open = false;
	let initial_viewport_height =
		window.visualViewport?.height || window.innerHeight;

	const tabs_list = $(".form-tabs-list");
	const tabs_content = this.tabs_content?.[0];

	if (!tabs_list.length || !tabs_content) {
		return;
	}

	const get_scroll_top = () => {
		return (
			window.scrollY ||
			document.documentElement.scrollTop ||
			document.body.scrollTop ||
			0
		);
	};

	const get_sticky_offset = () => {
		let offset = 12;

		const page_head = document.querySelector(".page-head");
		const form_tabs = document.querySelector(".form-tabs-list");

		if (page_head) {
			const style = window.getComputedStyle(page_head);
			const rect = page_head.getBoundingClientRect();

			if (
				style.display !== "none" &&
				style.visibility !== "hidden" &&
				rect.height > 0
			) {
				offset += rect.height;
			}
		}

		if (form_tabs) {
			const style = window.getComputedStyle(form_tabs);
			const rect = form_tabs.getBoundingClientRect();

			if (
				style.display !== "none" &&
				style.visibility !== "hidden" &&
				rect.height > 0
			) {
				offset += rect.height;
			}
		}

		return offset;
	};

	const set_tabs_sticky_up = () => {
		tabs_list
			.removeClass("form-tabs-sticky-down")
			.addClass("form-tabs-sticky-up");

		$(".page-head").css("top", "-15px");
	};

	const should_scroll_field = (input) => {
		if (!input || input.disabled || input.readOnly) {
			return false;
		}

		const input_type = String(input.type || "").toLowerCase();

		if (
			[
				"hidden",
				"checkbox",
				"radio",
				"button",
				"submit",
				"reset",
				"file",
				"color",
			].includes(input_type)
		) {
			return false;
		}

		return !$(input).closest(
			[
				".datepicker",
				".awesomplete > ul",
				".dropdown-menu",
			].join(",")
		).length;
	};

	const get_field_wrapper = (input) => {
		return (
			$(input)
				.closest(
					[
						".mobile-grid-card-field",
						".frappe-control",
						".form-group",
					].join(",")
				)
				.get(0) || input
		);
	};

	const scroll_field_into_visual_viewport = (element) => {
		if (!element) {
			return;
		}

		const viewport = window.visualViewport;
		const rect = element.getBoundingClientRect();
		const sticky_offset = get_sticky_offset();

		/*
		 * visualViewport.offsetTop dapat berubah pada iOS ketika keyboard
		 * terbuka atau halaman mengalami visual viewport shifting.
		 */
		const viewport_top =
			(viewport?.offsetTop || 0) + sticky_offset;

		const viewport_height =
			viewport?.height || window.innerHeight;

		const viewport_bottom =
			(viewport?.offsetTop || 0) +
			viewport_height -
			16;

		const field_top = rect.top;
		const field_bottom = rect.bottom;

		let scroll_delta = 0;

		if (field_top < viewport_top) {
			scroll_delta = field_top - viewport_top;
		} else if (field_bottom > viewport_bottom) {
			/*
			 * Prioritaskan field berada dekat bagian atas agar dropdown,
			 * datepicker, dan suggestion Link memiliki ruang.
			 */
			scroll_delta = field_top - viewport_top;
		} else {
			return;
		}

		window.scrollBy({
			top: scroll_delta,
			behavior: "smooth",
		});

		set_tabs_sticky_up();
	};

	$(window)
		.off("scroll.form-tabs")
		.on(
			"scroll.form-tabs",
			frappe.utils.throttle(() => {
				const current_scroll = get_scroll_top();

				if (
					current_scroll > 0 &&
					last_scroll <= current_scroll
				) {
					tabs_list
						.removeClass("form-tabs-sticky-down")
						.addClass("form-tabs-sticky-up");
				} else {
					tabs_list
						.removeClass("form-tabs-sticky-up")
						.addClass("form-tabs-sticky-down");
				}

				last_scroll = current_scroll;
			}, 500)
		);

	this.tab_link_container
		.off("click.form-tabs")
		.on("click.form-tabs", ".nav-link", (event) => {
			event.preventDefault();
			event.stopImmediatePropagation();

			$(event.currentTarget).tab("show");

			if (tabs_content.getBoundingClientRect().top < 100) {
				tabs_content.scrollIntoView({
					block: "start",
				});

				setTimeout(() => {
					set_tabs_sticky_up();
				}, 3);
			}
		});

	$(document)
		.off("focusin.form-field-scroll")
		.on(
			"focusin.form-field-scroll",
			[
				".frappe-control input",
				".frappe-control textarea",
				".frappe-control select",
				".mobile-grid-card-field-control input",
				".mobile-grid-card-field-control textarea",
				".mobile-grid-card-field-control select",
			].join(","),
			(event) => {
				const input = event.currentTarget;

				if (!should_scroll_field(input)) {
					return;
				}

				const field_wrapper = get_field_wrapper(input);

				/*
				 * Android umumnya selesai mengubah viewport dalam
				 * 200–350 ms. Ini menjadi fallback bila visualViewport
				 * tidak memicu resize.
				 */
				setTimeout(() => {
					scroll_field_into_visual_viewport(field_wrapper);
				}, 350);

				if (!window.visualViewport) {
					return;
				}

				const handle_viewport_resize = () => {
					const viewport_height =
						window.visualViewport.height;

					keyboard_open =
						viewport_height <
						initial_viewport_height * 0.8;

					if (keyboard_open) {
						requestAnimationFrame(() => {
							scroll_field_into_visual_viewport(
								field_wrapper
							);
						});
					}
				};

				window.visualViewport.addEventListener(
					"resize",
					handle_viewport_resize,
					{ once: true }
				);
			}
		);

	if (window.visualViewport) {
		window.visualViewport
			.removeEventListener(
				"resize",
				this._mobile_viewport_resize
			);

		this._mobile_viewport_resize = () => {
			const current_height =
				window.visualViewport.height;

			keyboard_open =
				current_height <
				initial_viewport_height * 0.8;

			if (!keyboard_open) {
				initial_viewport_height = Math.max(
					initial_viewport_height,
					current_height
				);
			}

			$("body").toggleClass(
				"mobile-keyboard-open",
				keyboard_open
			);
		};

		window.visualViewport.addEventListener(
			"resize",
			this._mobile_viewport_resize
		);
	}
}