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
        let roles = await this.get_default_roles(role_type);
        if (!roles || roles.length === 0) {
            roles = this.get_default_roles_if_empty(role_type);
        }
        return roles.some(role => frappe.user_roles.includes(role));
    }
    get_default_roles_if_empty(role_type) {
        let roles = {
            "bulk_edit_prices": ["Chief Sales Officer"],
        }
        return roles[role_type] || [];
    }
}
libya_customizations.utils = new Utils();