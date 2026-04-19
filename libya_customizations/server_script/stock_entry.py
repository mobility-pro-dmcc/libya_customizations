import frappe

def share_on_pending_submission(doc, method):
    # Retrieve the document state before the current save operation
    old_doc = doc.get_doc_before_save()
    
    # Ensure old_doc exists (it won't on the very first insertion)
    if not old_doc:
        return

    # Check if the state transitioned to "Pending Submission"
    if doc.workflow_state == "Pending Submission" and old_doc.workflow_state != "Pending Submission":
        
        # Determine the relevant warehouse (handling Issues, Receipts, and Transfers)
        target_warehouse = doc.to_warehouse or doc.from_warehouse
        
        if target_warehouse:
            warehouse_user = frappe.get_cached_value('Warehouse', target_warehouse, 'warehouse_user')
            
            if warehouse_user:
                frappe.share.add(
                    'Stock Entry',
                    doc.name,
                    warehouse_user,
                    read=1,
                    write=1,
                    submit=1,
                    notify=1
                )