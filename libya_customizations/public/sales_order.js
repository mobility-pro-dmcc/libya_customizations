{% include 'mobility_advanced_item_dialog/custom/common_popup.js' %}
frappe.ui.form.on("Sales Order", {
    onload(frm){
		
		frm.fields_dict.items.wrapper.onchange = function(){
			// frm.fields_dict.items.grid.grid_buttons.remove()
			frm.fields_dict.items.wrapper.querySelectorAll(".btn-open-row").forEach(function(btn){btn.remove();})
			frm.fields_dict.items.grid.grid_buttons[0].children[1].style.display = "none";
			frm.fields_dict.items.grid.grid_buttons[0].children[2].style.display = "none";
			frm.fields_dict.items.grid.grid_buttons[0].children[3].style.display = "none";
			frm.fields_dict['items'].grid.wrapper.find('.grid-delete-row').hide();
			frm.fields_dict.items.wrapper.querySelector(".grid-upload").style.display = "none";
			// frm.fields_dict.items.wrapper.querySelector(".grid-download").style.display = "none";
		}
        // frm.remove_custom_button("Update Items")
		if(frm.doc.docstatus === 1 && frm.doc.per_delivered !== 100){
			frm.remove_custom_button("Update Items")
			cur_frm.remove_custom_button("Update Items")
			frm.add_custom_button(__("Update Items"), () => {
				erpnext.utils.advanced_update_child_items({
					frm: frm,
					child_docname: "items",
					child_doctype: "Sales Order Detail",
					cannot_add_row: false,
					has_reserved_stock: frm.doc.__onload && frm.doc.__onload.has_reserved_stock,
				});
			});

			if(frm.doc.per_delivered !== 100 && frm.doc.docstatus == 1 && frm.doc.reservation_status == 'Reserve with Delivery' && !["On Hold", "Closed"].includes(frm.doc.status)){
				frappe.call({
					method: "frappe.client.has_permission",
					args: {
						doctype: "Delivery Note",
						docname: null,
						perm_type: "create"
					},
					callback: function(r) {
						if (r.message.has_permission) {
							frm.add_custom_button(__("Delivery Note "), function() {
								frappe.call({
									method: "libya_customizations.server_script.sales_order.create_dn_from_so",
									args: {
										doc: frm.doc
									},
									callback: function(r) {
										if (r.message) {
											const docname = r.message;
											frappe.set_route("Form", "Delivery Note", docname);
										}
									}
								});
							}, __("Create"));
						}
					}
				});
			}
		}
    },
	reservation_status(frm){
		if(!frappe.user_roles.includes("Chief Sales Officer") && frm.doc.reservation_status == "Reserve against Future Receipts")
			frappe.throw(_("You do not have the authority to choose Reserve against Future Receipts!"));
	},
    customer(frm){
        frappe.call({
            method: "libya_customizations.server_script.sales_order.get_customer_info", 
            args:{
                  customer : frm.doc.customer
            },
              callback: function(r){
                if(r.message && frm.doc.docstatus == 0){
                    frm.set_value(r.message[0]);
                }
            }
        })
    },
    after_save(frm){
        frappe.call({
            method: "libya_customizations.server_script.sales_order.get_customer_info", 
            args:{
                  customer : frm.doc.customer
            },
              callback: function(r){
                if(r.message && frm.doc.docstatus == 0){
                    frm.set_value(r.message[0]);
					frm.save();
                }
            }
        })
    }
})

frappe.ui.form.on('Sales Order', {
    before_cancel: function(frm) {
        frappe.call({
            method: 'libya_customizations.utils.get_linked_document',
            args: {
                linked_doctype: 'Delivery Note Item',
                docname: frm.doc.name,
                linked_field: 'against_sales_order',
				field: 'parent'
            },
            callback: function(response) {
                if (response.message) {
                    frappe.msgprint({
                        title: __('Cannot Cancel'),
                        message: __(`This Sales Order is linked to a Delivery Note ${response.message}`),
                        indicator: 'red'
                    });
                    frappe.validated = false;
                }
            }
        });
    }
});

erpnext.utils.advanced_update_child_items = function (opts) {
	const frm = opts.frm;
	const cannot_add_row = typeof opts.cannot_add_row === "undefined" ? true : opts.cannot_add_row;
	const child_docname = typeof opts.cannot_add_row === "undefined" ? "items" : opts.child_docname;
	const child_meta = frappe.get_meta(`${frm.doc.doctype} Item`);
	const has_reserved_stock = opts.has_reserved_stock ? true : false;
	const get_precision = (fieldname) => child_meta.fields.find((f) => f.fieldname == fieldname).precision;

	this.data = frm.doc[opts.child_docname].map((d) => {
		return {
			docname: d.name,
			name: d.name,
			item_code: d.item_code,
			item_name: d.item_name,
			delivery_date: d.delivery_date,
			schedule_date: d.schedule_date,
			conversion_factor: d.conversion_factor,
			production_year: d.production_year != null ? d.production_year : '',
			qty: d.qty,
			brand: d.brand,
			rate: d.rate,
			uom: d.uom,
			fg_item: d.fg_item,
			fg_item_qty: d.fg_item_qty,
		};
	});

	const fields = [
		{
			fieldtype: "Data",
			fieldname: "docname",
			read_only: 1,
			hidden: 1,
		},
		{
			fieldtype: "Link",
			fieldname: "brand",
			options: "Brand",
			read_only: 1,
			label: __("Brand"),
			in_list_view: 1,
			columns: 2,
		},
		{
			fieldtype: "Link",
			fieldname: "item_code",
			options: "Item",
			in_list_view: 0,
			read_only: 0,
			disabled: 0,
			label: __("Item Code"),
			get_query: function () {
				let filters;
				if (frm.doc.doctype == "Sales Order") {
					filters = { is_sales_item: 1 };
				} else if (frm.doc.doctype == "Purchase Order") {
					if (frm.doc.is_subcontracted) {
						if (frm.doc.is_old_subcontracting_flow) {
							filters = { is_sub_contracted_item: 1 };
						} else {
							filters = { is_stock_item: 0 };
						}
					} else {
						filters = { is_purchase_item: 1 };
					}
				}
				return {
					query: "erpnext.controllers.queries.item_query",
					filters: filters,
				};
			}
		},
		{
			fieldtype: "Data",
			fieldname: "item_name",
			default: 0,
			read_only: 0,
			in_list_view: 1,
			fetch_from: "item_code.item_name",
			label: __("Item Name"),
			columns: 5,
		},
		{
			fieldtype: "Link",
			fieldname: "uom",
			options: "UOM",
			read_only: 0,
			label: __("UOM"),
			reqd: 1,
			onchange: function () {
				frappe.call({
					method: "erpnext.stock.get_item_details.get_conversion_factor",
					args: { item_code: this.doc.item_code, uom: this.value },
					callback: (r) => {
						if (!r.exc) {
							if (this.doc.conversion_factor == r.message.conversion_factor) return;

							const docname = this.doc.docname;
							dialog.fields_dict.trans_items.df.data.some((doc) => {
								if (doc.docname == docname) {
									doc.conversion_factor = r.message.conversion_factor;
									dialog.fields_dict.trans_items.grid.refresh();
									return true;
								}
							});
						}
					},
				});
			},
		},
		{
			fieldtype: "Link",
			options: "Production Year",
			fieldname: "production_year",
			default: 0,
			read_only: 0,
			in_list_view: 1,
			label: __("Production"),
			columns: 1,
		},
		{
			fieldtype: "Float",
			fieldname: "qty",
			default: 0,
			read_only: 0,
			in_list_view: 1,
			label: __("Qty"),
			precision: get_precision("qty"),
			columns: 1,
		},
		{
			fieldtype: "Currency",
			fieldname: "rate",
			options: "currency",
			default: 0,
			read_only: 0,
			in_list_view: 1,
			label: __("Rate"),
			precision: get_precision("rate"),
			columns: 1,
		},
	];

	if (frm.doc.doctype == "Sales Order" || frm.doc.doctype == "Purchase Order") {
		fields.splice(2, 0, {
			fieldtype: "Date",
			fieldname: frm.doc.doctype == "Sales Order" ? "delivery_date" : "schedule_date",
			in_list_view: 0,
			label: frm.doc.doctype == "Sales Order" ? __("Delivery Date") : __("Reqd by date"),
			default: frm.doc.doctype == "Sales Order" ? frm.doc.delivery_date : frm.doc.schedule_date,
			reqd: 1,
		});
		fields.splice(3, 0, {
			fieldtype: "Float",
			fieldname: "conversion_factor",
			label: __("Conversion Factor"),
			precision: get_precision("conversion_factor"),
		});
	}

	if (
		frm.doc.doctype == "Purchase Order" &&
		frm.doc.is_subcontracted &&
		!frm.doc.is_old_subcontracting_flow
	) {
		fields.push(
			{
				fieldtype: "Link",
				fieldname: "fg_item",
				options: "Item",
				reqd: 1,
				in_list_view: 0,
				read_only: 0,
				disabled: 0,
				label: __("Finished Good Item"),
				get_query: () => {
					return {
						filters: {
							is_stock_item: 1,
							is_sub_contracted_item: 1,
							default_bom: ["!=", ""],
						},
					};
				},
			},
			{
				fieldtype: "Float",
				fieldname: "fg_item_qty",
				reqd: 1,
				default: 0,
				read_only: 0,
				in_list_view: 0,
				label: __("Finished Good Item Qty"),
				precision: get_precision("fg_item_qty"),
			}
		);
	}

	let dialog = new frappe.ui.Dialog({
		title: __("Update Items"),
		size: "extra-large",
		fields: [
			{
				fieldname: "trans_items",
				fieldtype: "Table",
				label: "Items",
				cannot_add_rows: cannot_add_row,
				in_place_edit: false,
				reqd: 1,
				data: this.data,
				get_data: () => {
					return this.data;
				},
				fields: fields,
			},
		],
		primary_action: function () {
			if (frm.doctype == "Sales Order" && has_reserved_stock) {
				this.hide();
				frappe.confirm(
					__(
						"The reserved stock will be released when you update items. Are you certain you wish to proceed?"
					),
					() => this.update_items()
				);
			} else {
				this.update_items();
			}
		},
		update_items: function () {
			const trans_items = this.get_values()["trans_items"].filter((item) => !!item.item_code);
			frappe.call({
				method: "libya_customizations.utils.update_child_qty_rate",
				freeze: true,
				args: {
					parent_doctype: frm.doc.doctype,
					trans_items: trans_items,
					parent_doctype_name: frm.doc.name,
					child_docname: child_docname,
				},
				callback: function () {
					frm.reload_doc();
				},
			});
			this.hide();
			refresh_field("items");
		},
		primary_action_label: __("Update"),
	});

	dialog.fields_dict.trans_items.grid.wrapper.on('change', '[data-fieldname="item_code"]', function(e) {
        let row = $(this).closest('.grid-row');
		console.log(row)
        let item_code = $(this).val();

        if (item_code) {
            // Fetch the item name from the server
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    'doctype': 'Item',
                    'filters': { 'name': item_code },
                    'fieldname': 'brand'
                },
                callback: function(r) {
                    if (r.message) {
                        // Update the item_name field in the table
                        let row_name = row.attr('data-name');
                        dialog.fields_dict.trans_items.grid.grid_rows_by_docname[row_name].doc.brand = r.message.brand;
                        dialog.fields_dict.trans_items.grid.refresh();
                    }
                }
            });
        } else {
            // Clear the item_name field if no item is selected
            let row_name = row.attr('data-name');
            dialog.fields_dict.trans_items.grid.grid_rows_by_docname[row_name].doc.brand = '';
            dialog.fields_dict.trans_items.grid.refresh();
        }
    });

	dialog.show();

	Array.from(dialog.fields_dict.trans_items.grid.grid_buttons[0].children).map(function(child, i){
		if( child.classList.contains("grid-add-row")){
			dialog.fields_dict.trans_items.grid.grid_buttons[0].children[i].style.display = "none";
		}
	})
	dialog.fields_dict.trans_items.wrapper.onchange = function(){
		Array.from(dialog.fields_dict.trans_items.grid.grid_buttons[0].children).map(function(child, i){
			if( child.classList.contains("grid-add-row")){
				dialog.fields_dict.trans_items.grid.grid_buttons[0].children[i].style.display = "none";
			}
		})		
	}

	dialog.fields_dict.trans_items.grid.add_custom_button("Get Items", ()=>{
		let display_columns = {
			"Item Code":'',
			"Brand":'',
			"Item Name":'',
			"Production Year":"",
			"Actual Stock":"",
			"Available Stock": "",
			"Selling Price":'',
		}
		if(frappe.user_roles.includes("Chief Sales Officer")){
			
			display_columns["Valuation Rate"]= "";
		}

		var dialog2 = new frappe.ui.form.AereleSelectDialog({
			doctype: "Sales Order",
			target: frm,
			cur_dialog: dialog,
			setters: [],
			display_columns,
			custom_method: 'mobility_advanced_item_dialog.custom.common_popup.get_item_details',
		})
	})
	  
};


frappe.ui.form.on("Sales Order", {
	onload_post_render(frm){
		const buttonsToRemove = [
			["Pick List", "Create"],
			["Delivery Note", "Create"],
			["Work Order", "Create"],
			["Sales Invoice", "Create"],
			["Material Request", "Create"],
			["Request for Raw Materials", "Create"],
			["Purchase Order", "Create"],
			["Project", "Create"],
			["Payment Request", "Create"],
			["Payment", "Create"],
			["Quotation", "Get Items From"]
        ];

        buttonsToRemove.forEach(([button, action]) => {
            frm.remove_custom_button(button, action);
        });
	},
    refresh: function(frm) {
		setTimeout(() => {
			const buttonsToRemove = [
				["Pick List", "Create"],
				["Delivery Note", "Create"],
				["Work Order", "Create"],
				["Sales Invoice", "Create"],
				["Material Request", "Create"],
				["Request for Raw Materials", "Create"],
				["Purchase Order", "Create"],
				["Project", "Create"],
				["Payment Request", "Create"],
				["Payment", "Create"],
				["Quotation", "Get Items From"]
			];
            buttonsToRemove.forEach(([button, action]) => {
                frm.remove_custom_button(button, action);
            });
			if(frm.doc.per_delivered === 100){
				frm.remove_custom_button("Hold", "Status");
				frm.remove_custom_button("Close", "Status");
			}
		},300);
		

        const delivery_status_info = {
            "Not Delivered": { color: "red", label: "Not Delivered" },
            "Partly Delivered": { color: "orange", label: "Partly Delivered" },
            "Fully Delivered": { color: "green", label: "Fully Delivered" }
        };

        // Get the delivery status field value
        let delivery_status = frm.doc.delivery_status;

        // Add the delivery status badge if it matches a key in delivery_status_info
        if (delivery_status_info[delivery_status] && frm.doc.docstatus === 1 && !["On Hold", "Closed"].includes(frm.doc.status)) {
			console.log(["On Hold", "Closed"].includes(frm.doc.status))
            // frm.page.set_indicator(_(delivery_status_info[delivery_status].label), delivery_status_info[delivery_status].color);
        }
    }
});




// disable rate auto update in child table
erpnext.TransactionController.prototype.item_code = function(doc, cdt, cdn){
	var me = this;
	frappe.flags.dialog_set = false;

	var item = frappe.get_doc(cdt, cdn);
	var update_stock = 0, show_batch_dialog = 0;

	item.weight_per_unit = 0;
	item.weight_uom = '';
	item.conversion_factor = 0;

	if(['Sales Invoice', 'Purchase Invoice'].includes(this.frm.doc.doctype)) {
		update_stock = cint(me.frm.doc.update_stock);
		show_batch_dialog = update_stock;

	} else if((this.frm.doc.doctype === 'Purchase Receipt') ||
		this.frm.doc.doctype === 'Delivery Note') {
		show_batch_dialog = 1;
	}

	if (show_batch_dialog && item.use_serial_batch_fields === 1) {
		show_batch_dialog = 0;
	}

	item.barcode = null;


	if(item.item_code || item.serial_no) {
		if(!me.validate_company_and_party()) {
			this.frm.fields_dict["items"].grid.grid_rows[item.idx - 1].remove();
		} else {
			item.pricing_rules = ''
			return this.frm.call({
				method: "libya_customizations.utils.get_item_details",
				child: item,
				args: {
					doc: me.frm.doc,
					args: {
						item_code: item.item_code,
						barcode: item.barcode,
						serial_no: item.serial_no,
						batch_no: item.batch_no,
						set_warehouse: me.frm.doc.set_warehouse,
						warehouse: item.warehouse,
						customer: me.frm.doc.customer || me.frm.doc.party_name,
						quotation_to: me.frm.doc.quotation_to,
						supplier: me.frm.doc.supplier,
						currency: me.frm.doc.currency,
						is_internal_supplier: me.frm.doc.is_internal_supplier,
						is_internal_customer: me.frm.doc.is_internal_customer,
						update_stock: update_stock,
						conversion_rate: me.frm.doc.conversion_rate,
						price_list: me.frm.doc.selling_price_list || me.frm.doc.buying_price_list,
						price_list_currency: me.frm.doc.price_list_currency,
						plc_conversion_rate: me.frm.doc.plc_conversion_rate,
						company: me.frm.doc.company,
						order_type: me.frm.doc.order_type,
						is_pos: cint(me.frm.doc.is_pos),
						is_return: cint(me.frm.doc.is_return),
						is_subcontracted: me.frm.doc.is_subcontracted,
						ignore_pricing_rule: me.frm.doc.ignore_pricing_rule,
						doctype: me.frm.doc.doctype,
						name: me.frm.doc.name,
						project: item.project || me.frm.doc.project,
						qty: item.qty || 1,
						net_rate: item.rate,
						base_net_rate: item.base_net_rate,
						stock_qty: item.stock_qty,
						conversion_factor: item.conversion_factor,
						weight_per_unit: item.weight_per_unit,
						uom: item.uom,
						weight_uom: item.weight_uom,
						manufacturer: item.manufacturer,
						stock_uom: item.stock_uom,
						pos_profile: cint(me.frm.doc.is_pos) ? me.frm.doc.pos_profile : '',
						cost_center: item.cost_center,
						tax_category: me.frm.doc.tax_category,
						item_tax_template: item.item_tax_template,
						child_doctype: item.doctype,
						child_docname: item.name,
						is_old_subcontracting_flow: me.frm.doc.is_old_subcontracting_flow,
						use_serial_batch_fields: item.use_serial_batch_fields,
						serial_and_batch_bundle: item.serial_and_batch_bundle,
						rate: item.rate,
					}
				},

				callback: function(r) {
					if(!r.exc) {
						frappe.run_serially([
							() => {
								if (item.docstatus === 0
									&& frappe.meta.has_field(item.doctype, "use_serial_batch_fields")
									&& !item.use_serial_batch_fields
									&& cint(frappe.user_defaults?.use_serial_batch_fields) === 1
								) {
									item["use_serial_batch_fields"] = 1;
								}
							},
							() => {
								var d = locals[cdt][cdn];
								me.add_taxes_from_item_tax_template(d.item_tax_rate);
								if (d.free_item_data && d.free_item_data.length > 0) {
									me.apply_product_discount(d);
								}
							},
							async () => {
								// for internal customer instead of pricing rule directly apply valuation rate on item
								const fetch_valuation_rate_for_internal_transactions = await frappe.db.get_single_value(
									"Accounts Settings", "fetch_valuation_rate_for_internal_transaction"
								);
								if ((me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) && fetch_valuation_rate_for_internal_transactions) {
									me.get_incoming_rate(item, me.frm.posting_date, me.frm.posting_time,
										me.frm.doc.doctype, me.frm.doc.company);
								} else {
// 										me.frm.script_manager.trigger("price_list_rate", cdt, cdn);
								}
							},
							() => {
								if (me.frm.doc.is_internal_customer || me.frm.doc.is_internal_supplier) {
									me.calculate_taxes_and_totals();
								}
							},
							() => me.toggle_conversion_factor(item),
							() => {
								if (show_batch_dialog && !frappe.flags.trigger_from_barcode_scanner)
									return frappe.db.get_value("Item", item.item_code, ["has_batch_no", "has_serial_no"])
										.then((r) => {
											if (r.message &&
											(r.message.has_batch_no || r.message.has_serial_no)) {
												frappe.flags.hide_serial_batch_dialog = false;
											} else {
												show_batch_dialog = false;
											}
										});
							},
							() => {
								// check if batch serial selector is disabled or not
								if (show_batch_dialog && !frappe.flags.hide_serial_batch_dialog)
									return frappe.db.get_single_value('Stock Settings', 'disable_serial_no_and_batch_selector')
										.then((value) => {
											if (value) {
												frappe.flags.hide_serial_batch_dialog = true;
											}
										});
							},
							() => {
								if(show_batch_dialog && !frappe.flags.hide_serial_batch_dialog && !frappe.flags.dialog_set) {
									var d = locals[cdt][cdn];
									$.each(r.message, function(k, v) {
										if(!d[k]) d[k] = v;
									});

									if (d.has_batch_no && d.has_serial_no) {
										d.batch_no = undefined;
									}

									frappe.flags.dialog_set = true;
									erpnext.show_serial_batch_selector(me.frm, d, (item) => {
										me.frm.script_manager.trigger('qty', item.doctype, item.name);
										if (!me.frm.doc.set_warehouse)
											me.frm.script_manager.trigger('warehouse', item.doctype, item.name);
										me.apply_price_list(item, true);
									}, undefined, !frappe.flags.hide_serial_batch_dialog);
								} else {
									frappe.flags.dialog_set = false;
								}
							},
							() => me.conversion_factor(doc, cdt, cdn, true),
							() => me.remove_pricing_rule(item),
							() => {
								if (item.apply_rule_on_other_items) {
									let key = item.name;
									me.apply_rule_on_other_items({key: item});
								}
							},
							() => {
								var company_currency = me.get_company_currency();
								me.update_item_grid_labels(company_currency);
							}
						]);
					}
				}
			});
		}
	}
}
erpnext.TransactionController.prototype.apply_price_list = () => {};

frappe.ui.form.on('Sales Order Item', {
    item_code: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        let duplicate = frm.doc.items.find(
            d => d.item_code === row.item_code && d.name !== row.name
        );

        if (duplicate) {
            frappe.msgprint(__('Item {0} is already added in Row {1}', [row.item_code, duplicate.idx]));
            
            // remove the current row
            frm.get_field("items").grid.grid_rows_by_docname[row.name].remove();
            frm.refresh_field("items");
        }
    }
});