frappe.ui.form.on("Journal Entry", {
  	refresh:function(frm){
      	if(cur_frm.doc.custom_voucher_no){
            frm.disable_save();
            frm.page.clear_primary_action();
            frm.page.clear_secondary_action();
        }
    }
});