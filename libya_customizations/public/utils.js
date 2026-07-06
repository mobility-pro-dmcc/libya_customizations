frappe.provide("libya_customizations.utils")

class Utils {
    async get_default_roles(role_type) {
        let roles = await frappe.call({
            method: "libya_customizations.utils.get_default_roles",
            args: {
                role_type: role_type
            }
        });
        return roles.message;
    }
    async check_roles_included(role_type) {
        let check_roles = await frappe.call({
            method: "libya_customizations.utils.check_roles_included",
            args: {
                role_type: role_type
            }
        });
        return check_roles.message;
    }
    async get_default_roles_if_empty(role_type) {
        let roles = await frappe.call({
            method: "libya_customizations.utils.get_default_roles_if_empty",
            args: {
                role_type: role_type
            }
        });
        return roles.message;
    }
}
libya_customizations.utils = new Utils();