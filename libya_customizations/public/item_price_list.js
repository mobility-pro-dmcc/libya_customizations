frappe.listview_settings['Item Price'] = {
    onload: async function (listview) {        
        // 2. Add the "In-Stock Items" button
        listview.page.add_inner_button(__('In-Stock Items'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([
                ['Item Price', 'stock_qty', '>', 0]
            ]);
            listview.refresh();
        }, "Filters");

        // 3. Add the "Available Items" button
        listview.page.add_inner_button(__('Available Items'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([
                ['Item Price', 'Available_qty', '>', 0]
            ]);
            listview.refresh();
        }, "Filters");        
        
        // 4. Add the "Not Priced Items" button
        listview.page.add_inner_button(__('Non-Priced Items'), function () {
            listview.filter_area.clear();
            listview.filter_area.add([
                ['Item Price', 'price_list_rate', '=', 0],
                ['Item Price', 'stock_valuation_rate', '>', 0],
                ['Item Price', 'selling', '=', 1]
            ]);
            listview.refresh();
        }, "Filters");

        // 5. Add the "Non-Profitable Items" button
        listview.page.add_inner_button(__('Non-Profitable Items'), function () {
            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Item Price',
                    fields: ['name', 'price_list_rate', 'stock_valuation_rate'],
                    filters: [
                        ['Item Price', 'price_list_rate', '>', 0],
                        ['Item Price', 'stock_valuation_rate', '>', 0],
                        ['Item Price', 'selling', '=', 1]
                    ],
                    limit_page_length: 10000
                },
                callback: function(response) {
                    if (response.message && response.message.length > 0) {
                        const filteredItemNames = response.message
                            .filter(item => item.price_list_rate < item.stock_valuation_rate)
                            .map(item => item.name);

                        if (filteredItemNames.length > 0) {
                            listview.filter_area.clear();
                            listview.filter_area.add([
                                ['Item Price', 'name', 'in', filteredItemNames]
                            ]);
                            listview.refresh();
                        }
                    }
                }
            });
        }, "Filters");

        // 4. Role-based buttons
        if (await libya_customizations.utils.check_roles_included("bulk_edit_prices")) {
            // 4.1 Increase Item Prices
            listview.page.add_inner_button(__('Increase Item Prices'), function () {
                let dialog = new frappe.ui.Dialog({
                    title: __('Increase Item Prices by Percentage'),
                    fields: [
                        {
                            fieldtype: 'Percent',
                            fieldname: 'increase_percent',
                            label: __('Increase Percent'),
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Apply'),
                    primary_action(values) {
                        frappe.call({
                            method: 'libya_customizations.server_script.item_price.increase_item_price',
                            args: {
                                percent: values.increase_percent,
                                filters: listview.filter_area.get()
                            },
                            callback: () => {
                                cur_list.refresh();
                            }
                        });
                        dialog.hide();
                    }
                });
                dialog.show();
            });

            // 4.2 Export Item Prices
            listview.page.add_inner_button(__('Export Item Prices'), function () {
                frappe.call({
                    method: 'libya_customizations.server_script.item_price.export_item_price_data',
                    args: {
                        filters: listview.filter_area.get()
                    },
                    callback: function (response) {
                        if (response.message) {
                            const download_link = document.createElement('a');
                            download_link.href = response.message;
                            download_link.download = 'Item Price.xlsx';
                            document.body.appendChild(download_link);
                            download_link.click();
                            document.body.removeChild(download_link);
                        } else {
                            frappe.msgprint(__('Unable to export data.'));
                        }
                    }
                });
            }, "Import & Export");

            // 4.3 Import Item Prices
            listview.page.add_inner_button(__('Import Item Prices'), function () {
                var dialog = new frappe.ui.Dialog({
                    title: __('Import Item Prices'),
                    fields: [
                        {
                            fieldtype: 'Attach',
                            fieldname: 'file',
                            label: __('Select Excel File'),
                            reqd: true
                        }
                    ],
                    primary_action_label: __('Update'),
                    primary_action: function () {
                        var values = dialog.get_values();
                        if (values && values.file) {
                            upload_and_import(values.file);
                            dialog.hide();
                        }
                    }
                });
                dialog.show();
            }, "Import & Export");
        }
    }
};

// Utility function for import
function upload_and_import(file) {
    var formData = new FormData();
    formData.append('file', file);

    frappe.call({
        method: 'libya_customizations.server_script.item_price.import_item_price_data',
        args: {
            file_url: file
        },
        freeze: true,
        freeze_message: __('Uploading and Importing Data...'),
        callback: function(response) {
            if (response.message) {
                frappe.msgprint(__('File uploaded and Item Prices imported successfully.'));
                frappe.views.ListView.refresh();
            } else {
                frappe.msgprint(__('Error occurred while importing the data.'));
            }
        }
    });
}