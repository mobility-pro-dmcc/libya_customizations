import frappe

def execute():
    doctype = "Journal Entry Account"
    field = "reference_type"
    new_option = "Account Closing Voucher"

    meta = frappe.get_meta(doctype)
    field_meta = meta.get_field(field)
    
    if not field_meta:
        return

    current_options = field_meta.options.split("\n") if field_meta.options else []

    property_setter = frappe.db.get_value(
        "Property Setter", 
        {"doc_type": doctype, "field_name": field, "property": "options"}, 
        ["name", "value"], 
        as_dict=True
    )

    if property_setter:
        ps_options = property_setter.value.split("\n")
        for opt in ps_options:
            if opt.strip() and opt not in current_options:
                current_options.append(opt)
        
        frappe.delete_doc("Property Setter", property_setter.name)

    if new_option not in current_options:
        current_options.append(new_option)

    new_options_str = "\n".join(current_options)
    field_meta.options = new_options_str
    field_meta.save()
    frappe.db.commit()
    print(f"Added '{str(new_options_str)}' to options of field '{field}' in doctype '{doctype}'")
    frappe.clear_cache(doctype=doctype)