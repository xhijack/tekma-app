frappe.ui.form.on('Sales Invoice', {
  

  refresh(frm) {
    // Tambahkan tombol hanya jika tidak sedang loading dan outstanding > 0
    if (!frm._ar_loading && Number(frm.doc.current_outstanding || 0) > 0) {
      frm.add_custom_button(__('Lihat Piutang'), () => open_ar_dialog(frm));
    }
  },

  customer(frm) {
    frm._ar_loading = true;
    fetch_ar_summary(frm);
  },

  company(frm) {
    frm._ar_loading = true;
    fetch_ar_summary(frm);
  },
});

function fetch_ar_summary(frm) {
  const { customer, company } = frm.doc || {};
  if (!customer || !company) {
    frm._ar_loading = false;
    return;
  }

  frappe.call({
    method: 'tekma_app.api.get_ar_summary_by_customer',
    args: { company, customer },
    callback: (r) => {
      const data = (r && r.message) ? r.message : {};
      const outstanding = data.outstanding_amount || 0;

      // set_value akan memicu refresh -> tombol akan ditambahkan di handler refresh
      frm.set_value('current_outstanding', outstanding);
      frm._ar_loading = false;
      // jika butuh memastikan tombol langsung muncul:
      // frm.refresh();
    },
    error: () => {
      frm._ar_loading = false;
    }
  });
}

function open_ar_dialog(frm) {
  const { company, customer } = frm.doc || {};
  if (!company || !customer) return;

  // Dialog dengan field HTML agar konten stabil
  const d = new frappe.ui.Dialog({
    title: __('Daftar Piutang'),
    size: 'large',
    fields: [
      { fieldtype: 'HTML', fieldname: 'ar_html' }
    ],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();

  const html_field = d.get_field('ar_html');
  const $wrap = html_field && html_field.$wrapper ? html_field.$wrapper : null;
  if (!$wrap) return;

  $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

  frappe.call({
    method: 'tekma_app.api.get_ar_invoices_by_customer',
    args: { company, customer },
    callback: (r) => {
      const payload = (r && r.message) ? r.message : {};
      const currency = payload.currency || frm.doc.currency || frappe.defaults.get_default('currency') || 'IDR';
      const invoices = payload.invoices || [];
      const totals = payload.totals || { grand_total: 0, paid_amount: 0, outstanding_amount: 0 };

      const fmt = (v) => format_currency(v || 0, currency);

      const header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:140px">${__('Tanggal Invoice')}</th>
            <th style="text-align:left">${__('Nomor Invoice')}</th>
            <th style="text-align:right;width:140px">${__('Grand Total')}</th>
            <th style="text-align:right;width:140px">${__('Paid Amount')}</th>
            <th style="text-align:right;width:140px">${__('Outstanding')}</th>
          </tr>
        </thead>
      `;

      let rows_html = '';
      invoices.forEach((inv, idx) => {
        rows_html += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(inv.posting_date)}</td>
            <td>
              <a href="/app/sales-invoice/${encodeURIComponent(inv.name)}" target="_blank" rel="noopener">
                ${frappe.utils.escape_html(inv.name)}
              </a>
            </td>
            <td style="text-align:right">${fmt(inv.grand_total)}</td>
            <td style="text-align:right">${fmt(inv.paid_amount)}</td>
            <td style="text-align:right"><b>${fmt(inv.outstanding_amount)}</b></td>
          </tr>
        `;
      });

      const totals_html = `
        <tr>
          <td colspan="3" style="text-align:right"><b>${__('Total')}</b></td>
          <td style="text-align:right"><b>${fmt(totals.grand_total)}</b></td>
          <td style="text-align:right"><b>${fmt(totals.paid_amount)}</b></td>
          <td style="text-align:right"><b>${fmt(totals.outstanding_amount)}</b></td>
        </tr>
      `;

      const body_html = `
        <div style="overflow:auto; max-height:60vh">
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${header}
            <tbody>
              ${rows_html || `<tr><td colspan="6" style="text-align:center; color:#888">${__('Tidak ada data')}</td></tr>`}
              ${totals_html}
            </tbody>
          </table>
        </div>
      `;

      $wrap.html(body_html);
    },
    error: () => {
      $wrap.html(`<div class="text-danger">${__('Gagal memuat data.')}</div>`);
    }
  });
}

frappe.ui.form.on('Sales Invoice Item', {
  check_price(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row || !row.item_code) {
      frappe.msgprint({ message: __('Pilih Item terlebih dahulu.'), indicator: 'orange' });
      return;
    }
    open_item_price_dialog(frm, row);
  }
});

function open_item_price_dialog(frm, row) {
  // kalau dipanggil dari tombol header (lihat piutang), row bisa undefined
  const { company, customer } = frm.doc || {};
  if (!company) {
    frappe.msgprint({ message: __('Company belum dipilih.'), indicator: 'orange' });
    return;
  }

  const item_code = row?.item_code;
  if (!item_code) {
    frappe.msgprint({ message: __('Pilih Item terlebih dahulu.'), indicator: 'orange' });
    return;
  }

  const d = new frappe.ui.Dialog({
    title: __('Riwayat Harga • {0}', [frappe.utils.escape_html(item_code)]),
    size: 'large', // kita override width manual di bawah
    fields: [{ fieldtype: 'HTML', fieldname: 'price_html' }],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();

  // Perlebar dialog
  try {
    d.$wrapper.find('.modal-dialog').css({ 'max-width': '1200px', 'width': '95%' });
  } catch (e) { /* ignore */ }

  const $wrap = d.get_field('price_html').$wrapper;
  $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

  frappe.call({
    method: 'tekma_app.api.get_item_price_history',
    args: {
      company,
      item_code,
      customer: customer || undefined,
      limit: 100
    },
    callback: (r) => {
      const data = (r && r.message) ? r.message : {};
      const rows = data.rows || [];
      const currency = frm.doc.currency || frappe.defaults.get_default('currency') || 'IDR';
      const fmt = (v) => format_currency(v || 0, currency);

      // gaya kecil + rapat
      const style = `
        <style>
          .ar-price-dialog { font-size: 12px; }
          .ar-price-dialog table.table th,
          .ar-price-dialog table.table td { padding: 4px 8px; vertical-align: middle; }
        </style>
      `;

      const header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:120px">${__('Tanggal Invoice')}</th>
            <th style="text-align:left">${__('Nomor Invoice')}</th>
            <th style="text-align:right;width:90px">${__('Qty')}</th>
            <th style="text-align:left;width:80px">${__('UOM')}</th>
            <th style="text-align:right;width:100px">${__('% Disc')}</th>
            <th style="text-align:right;width:120px">${__('Rate')}</th>
            <th style="text-align:right;width:140px">${__('Net Amount')}</th>
          </tr>
        </thead>
      `;

      let rows_html = '';
      rows.forEach((it, idx) => {
        rows_html += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(it.posting_date)}</td>
            <td>
              <a href="/app/sales-invoice/${encodeURIComponent(it.invoice)}" target="_blank" rel="noopener">
                ${frappe.utils.escape_html(it.invoice)}
              </a>
            </td>
            <td style="text-align:right">${frappe.format(it.qty, {fieldtype: 'Float'})}</td>
            <td>${frappe.utils.escape_html(it.uom || '')}</td>
            <td style="text-align:right">${frappe.format(it.discount_percentage || 0, {fieldtype: 'Percent'})}</td>
            <td style="text-align:right">${fmt(it.rate)}</td>
            <td style="text-align:right"><b>${fmt(it.net_amount)}</b></td>
          </tr>
        `;
      });

      const body_html = `
        ${style}
        <div class="ar-price-dialog" style="overflow:auto; max-height:70vh">
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${header}
            <tbody>
              ${rows_html || `<tr><td colspan="8" style="text-align:center; color:#888">${__('Tidak ada data')}</td></tr>`}
            </tbody>
          </table>
        </div>
        <div class="mt-2 text-muted">${__('Baris ditampilkan')}: ${rows.length}</div>
      `;

      $wrap.html(body_html);
    },
    error: () => {
      $wrap.html(`<div class="text-danger">${__('Gagal memuat data.')}</div>`);
    }
  });
}
