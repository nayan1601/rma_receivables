frappe.query_reports["Journal Receivables Ledger"] = {
  "filters": [
    {"fieldname":"company","label":__("Company"),"fieldtype":"Link","options":"Company","default":frappe.defaults.get_user_default("Company"),"reqd":1},
    {"fieldname":"customer","label":__("Customer"),"fieldtype":"Link","options":"Customer"},
    {"fieldname":"from_date","label":__("From Date"),"fieldtype":"Date","default":frappe.datetime.add_months(frappe.datetime.get_today(), -1),"reqd":1},
    {"fieldname":"to_date","label":__("To Date"),"fieldtype":"Date","default":frappe.datetime.get_today(),"reqd":1},
    {"fieldname":"receivable_type","label":__("Transaction Type"),"fieldtype":"Select","options":"\nInvoice\nPayment\nCredit Note\nDebit Note\nAdjustment"}
  ],
  "formatter": function(value, row, column, data, default_formatter) {
    value = default_formatter(value, row, column, data);
    if (column.fieldname === "balance" && data && data.balance < 0) value = "<span style='color:red'>" + value + "</span>";
    if (column.fieldname === "receivable_type") {
      var color_map = {"Invoice":"blue","Payment":"green","Credit Note":"orange","Debit Note":"purple","Adjustment":"gray"};
      if (data && color_map[data.receivable_type]) value = "<span style='color:" + color_map[data.receivable_type] + "'>" + value + "</span>";
    }
    return value;
  }
};
