frappe.ui.form.on('Stock Entry', {
  refresh(frm) {
    apply_prod_reference_query(frm);
  },
   async update_ratio_valuation_rate(frm) {
    if (!frm.doc.items || !frm.doc.items.length) {
      frappe.msgprint(__('Tidak ada baris Item.'));
      return;
    }

    try {
      frappe.dom.freeze(__('Menghitung valuation per ratio...'));
      const r = await frappe.call({
        method: "tekma_app.utils.compute_valuation_rates",
        args: {
          doc: frm.doc,
          rounding: 0,            // ubah ke 2 kalau ingin 2 desimal
          ratio_field: "ratio"    // nama field ratio di Item
        }
      });
      frappe.dom.unfreeze();

      const res = r && r.message;
      if (!res) return;

      let updated = 0;
      (frm.doc.items || []).forEach(row => {
        const is_fg = row.t_warehouse && !row.s_warehouse; // baris FG
        const info = res[row.item_code];
        if (!is_fg || !info) return;

        const vr = flt(info.valuation_rate);

        // Set semua field rate supaya UI konsisten
        row.basic_rate   = vr;                         // dipakai perhitungan
        row.valuation_rate = vr;                       // tampilkan di kolom "Valuation Rate"
        row.rate         = vr;                         // beberapa versi pakai 'rate'
        row.basic_amount = vr * flt(row.qty || 0);     // agar kolom amount langsung update

        updated++;
      });

      frm.dirty();
      frm.refresh_field('items');

      const m = res._meta || {};
      // frappe.msgprint({
      //   title: __('Selesai'),
      //   message: `
      //     Total RM Cost: <b>${format_currency(m.total_rm_cost || 0, frm.doc.currency || 'IDR')}</b><br>
      //     Dialokasikan: <b>${format_currency(m.sum_allocated || 0, frm.doc.currency || 'IDR')}</b><br>
      //     Selisih: <b>${format_currency(m.difference || 0, frm.doc.currency || 'IDR')}</b><br>
      //     Baris FG terupdate: <b>${updated}</b>
      //   `,
      //   indicator: (m.difference || 0) === 0 ? 'green' : 'orange'
      // });
      await frm.save();
    } catch (e) {
      frappe.dom.unfreeze();
      console.error(e);
      frappe.msgprint({title: __('Error'), message: __('Gagal menghitung.'), indicator: 'red'});
    }
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

function flt(v) { const n = parseFloat(v); return isNaN(n) ? 0 : n; }