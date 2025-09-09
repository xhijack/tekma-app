frappe.ui.form.on('Stock Entry', {
  refresh(frm) {
    apply_prod_reference_query(frm);
  },

  stock_entry_type(frm) {
    apply_prod_reference_query(frm);
    if (frm.doc.stock_entry_type === 'Mincer' || frm.doc.stock_entry_type === 'Mixer' || frm.doc.stock_entry_type === 'Flaker') {
      frm.doc.from_bom = 1;
      frm.doc.use_multi_level_bom = 0
      frm.refresh_field('from_bom');
      
      frm.set_query('bom_no', function() {
      return {
        filters: {
          production_type: frm.doc.stock_entry_type,
          docstatus: 1  // Only submitted documents
        }
      };
    });
      
    }
  }
});

function apply_prod_reference_query(frm) {
  if (frm.doc.stock_entry_type === 'Mincer') {
    // When Sales Order's stock_entry_type is Mincer,
    // filter prod_reference to only records with stock_entry_type = Flaker
    frm.set_query('prod_reference', function() {
      return {
        filters: {
          stock_entry_type: 'Flaker',
          docstatus: 1  // Only submitted documents
        }
      };
    });
  } else if (frm.doc.stock_entry_type === 'Mixer') {
    // When Sales Order's stock_entry_type is Mincer,
    // filter prod_reference to only records with stock_entry_type = Flaker
    frm.set_query('prod_reference', function() {
      return {
        filters: {
          stock_entry_type: 'Mincer',
          docstatus: 1  // Only submitted documents
        }
      };
    });
  }else if (frm.doc.stock_entry_type === 'Wrap') {
    // When Sales Order's stock_entry_type is Mincer,
    // filter prod_reference to only records with stock_entry_type = Flaker
    frm.set_query('prod_reference', function() {
      return {
        filters: {
          stock_entry_type: 'Mixer',
          docstatus: 1  // Only submitted documents
        }
      };
    });
  } else {
    // For other values, remove the filter (show all)
    frm.set_query('prod_reference', function() {
      return {};
    });
  }
}

frappe.ui.form.on('Stock Entry Detail', {
        item_code(frm, cdt, cdn) {
            const row = frappe.get_doc(cdt, cdn);
            if (frm.doc.stock_entry_type === 'Wrap') {
                frappe.model.set_value(cdt, cdn, 'set_basic_rate_manually', 1);
            }
        }
})