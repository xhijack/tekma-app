frappe.ui.form.on('Delivery Note', {
  

  refresh(frm) {
    // Tambahkan tombol hanya jika tidak sedang loading dan outstanding > 0
    if (!frm._ar_loading && Number(frm.doc.current_outstanding || 0) > 0) {
      frm.add_custom_button(__('Lihat Piutang'), () => open_ar_dialog(frm));
      if (frm.doc.customer) {
        frm.add_custom_button(__('History Tiang'), () => open_tiang_history_dialog(frm));
      }
    }
  },

  customer(frm) {
    frm._ar_loading = true;
    fetch_ar_summary(frm);
    if (frm.doc.customer) {
      frm.add_custom_button(__('History Tiang'), () => open_tiang_history_dialog(frm));
    }
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

  const d = new frappe.ui.Dialog({
    title: __('Daftar Piutang'),
    size: 'large',
    fields: [{ fieldtype: 'HTML', fieldname: 'ar_html' }],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();
  try { d.$wrapper.find('.modal-dialog').css({ 'max-width': '1400px', 'width': '95%' }); } catch (e) {}

  const $wrap = d.get_field('ar_html').$wrapper;
  $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

  frappe.call({
    method: 'tekma_app.api.get_ar_invoices_by_customer',
    args: { company, customer },
    callback: (r) => {
      const payload = (r && r.message) ? r.message : {};
      const currency = payload.currency || frm.doc.currency || frappe.defaults.get_default('currency') || 'IDR';

      const invoices = payload.invoices || [];
      const totals = payload.totals || { grand_total: 0, paid_amount: 0, outstanding_amount: 0, applied_credit_from_returns: 0 };
      const xadj = payload.totals_adjusted || { invoices_outstanding_adjusted: 0 };
      const credit_notes = payload.credit_notes || [];
      const advances = payload.advances || [];
      const x = payload.totals_extended || {
        invoices_outstanding_adjusted: 0,
        credit_note_available: 0,
        advance_unallocated: 0,
        net_receivable: 0
      };

      const fmt = (v) => format_currency(v || 0, currency);

      const style = `
        <style>
          .ar-dialog { font-size: 12px; }
          .ar-dialog table.table th,
          .ar-dialog table.table td { padding: 4px 8px; vertical-align: middle; }
          .ar-section-title { margin: 8px 0; font-weight: 600; }
          .ar-summary { margin-top: 8px; }
          .ar-summary .row { display: flex; gap: 16px; flex-wrap: wrap; }
          .ar-summary .box { padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 6px; background: #fafafa; }
          .muted { color: #6b7280; font-size: 11px; }
        </style>
      `;

      // Invoices (Adjusted Outstanding)
      const inv_header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:120px">${__('Tanggal Invoice')}</th>
            <th style="text-align:left">${__('Nomor Invoice')}</th>
            <th style="text-align:left;width:220px">${__('Remarks')}</th>
            <th style="text-align:right;width:140px">${__('Grand Total')}</th>
            <th style="text-align:right;width:140px">${__('Paid Amount')}</th>
            <th style="text-align:right;width:180px">${__('Outstanding (Adjusted)')}</th>
          </tr>
        </thead>
      `;

      let inv_rows = '';
      invoices.forEach((inv, idx) => {
        const applied_note = (inv.applied_credit && inv.applied_credit > 0)
          ? `<div class="muted">(- ${__('Credit Note')} ${fmt(inv.applied_credit)})</div>` : '';
        inv_rows += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(inv.posting_date)}</td>
            <td><a href="/app/sales-invoice/${encodeURIComponent(inv.name)}" target="_blank" rel="noopener">${frappe.utils.escape_html(inv.name)}</a></td>
            <td>${frappe.utils.escape_html(inv.remarks || '')}</td>
            <td style="text-align:right">${fmt(inv.grand_total)}</td>
            <td style="text-align:right">${fmt(inv.paid_amount)}</td>
            <td style="text-align:right"><b>${fmt(inv.adjusted_outstanding)}</b>${applied_note}</td>
          </tr>
        `;
      });

      const inv_totals = `
        <tr>
          <td colspan="4" style="text-align:right"><b>${__('Total')}</b></td>
          <td style="text-align:right"><b>${fmt(totals.grand_total)}</b></td>
          <td style="text-align:right"><b>${fmt(totals.paid_amount)}</b></td>
          <td style="text-align:right"><b>${fmt(xadj.invoices_outstanding_adjusted)}</b></td>
        </tr>
      `;

      // Credit Notes (remaining / not fully applied)
      const cn_header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:120px">${__('Tanggal')}</th>
            <th style="text-align:left">${__('Credit Note')}</th>
            <th style="text-align:left;width:160px">${__('Return Against')}</th>
            <th style="text-align:right;width:160px">${__('Available Credit')}</th>
          </tr>
        </thead>
      `;
      let cn_rows = '';
      credit_notes.forEach((cn, idx) => {
        const ra = cn.return_against
          ? `<a href="/app/sales-invoice/${encodeURIComponent(cn.return_against)}" target="_blank" rel="noopener">${frappe.utils.escape_html(cn.return_against)}</a>`
          : `<span class="muted">-</span>`;
        cn_rows += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(cn.posting_date)}</td>
            <td><a href="/app/sales-invoice/${encodeURIComponent(cn.name)}" target="_blank" rel="noopener">${frappe.utils.escape_html(cn.name)}</a></td>
            <td>${ra}</td>
            <td style="text-align:right"><b>${fmt(cn.available_amount)}</b></td>
          </tr>
        `;
      });

      // Advances (unallocated)
      const adv_header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:120px">${__('Tanggal')}</th>
            <th style="text-align:left">${__('Payment Entry')}</th>
            <th style="text-align:right;width:160px">${__('Unallocated Amount')}</th>
          </tr>
        </thead>
      `;
      let adv_rows = '';
      advances.forEach((pe, idx) => {
        adv_rows += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(pe.posting_date)}</td>
            <td><a href="/app/payment-entry/${encodeURIComponent(pe.name)}" target="_blank" rel="noopener">${frappe.utils.escape_html(pe.name)}</a></td>
            <td style="text-align:right"><b>${fmt(pe.unallocated_amount)}</b></td>
          </tr>
        `;
      });

      // Summary
      const summary_html = `
        <div class="ar-summary">
          <div class="row">
            <div class="box">${__('Invoices Outstanding (Adjusted)')}: <b>${fmt(x.invoices_outstanding_adjusted)}</b></div>
            <div class="box">${__('Credit Note Available (Remaining)')}: <b>${fmt(x.credit_note_available)}</b></div>
            <div class="box">${__('Advance (Unallocated)')}: <b>${fmt(x.advance_unallocated)}</b></div>
            <div class="box">${__('Net Receivable')}: <b>${fmt(x.net_receivable)}</b></div>
          </div>
        </div>
      `;

      const html = `
        ${style}
        <div class="ar-dialog" style="overflow:auto; max-height:72vh">
          <div class="ar-section-title">${__('Invoices (Outstanding, Adjusted with Returns)')}</div>
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${inv_header}
            <tbody>
              ${inv_rows || `<tr><td colspan="7" style="text-align:center; color:#888">${__('Tidak ada data')}</td></tr>`}
              ${inv_rows ? inv_totals : ''}
            </tbody>
          </table>

          <div class="ar-section-title">${__('Credit Notes (Remaining)')}</div>
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${cn_header}
            <tbody>
              ${cn_rows || `<tr><td colspan="5" style="text-align:center; color:#888">${__('Tidak ada credit note tersedia')}</td></tr>`}
            </tbody>
          </table>

          <div class="ar-section-title">${__('Advances / Dana Menggantung')}</div>
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${adv_header}
            <tbody>
              ${adv_rows || `<tr><td colspan="4" style="text-align:center; color:#888">${__('Tidak ada dana menggantung')}</td></tr>`}
            </tbody>
          </table>

          ${summary_html}
        </div>
      `;

      $wrap.html(html);
    },
    error: () => {
      $wrap.html(`<div class="text-danger">${__('Gagal memuat data.')}</div>`);
    }
  });
}


frappe.ui.form.on('Delivery Note Item', {
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
    size: 'large',
    fields: [
      { fieldtype: 'HTML', fieldname: 'controls_html' },
      { fieldtype: 'HTML', fieldname: 'price_html' }
    ],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();

  try {
    d.$wrapper.find('.modal-dialog').css({ 'max-width': '1200px', 'width': '95%' });
  } catch (e) { /* ignore */ }

  const $controls = d.get_field('controls_html').$wrapper;
  const $wrap = d.get_field('price_html').$wrapper;

  // Render page-size control (default 20)
  const controlHtml = `
    <div style="display:flex;justify-content:flex-end;gap:8px;margin-bottom:6px;align-items:center">
      <span class="text-muted" style="font-size:11px">${__('Tampilkan')}</span>
      <select class="form-control input-sm" style="width:auto" data-role="page-size">
        <option value="20" selected>20</option>
        <option value="50">50</option>
        <option value="100">100</option>
        <option value="500">500</option>
      </select>
      <span class="text-muted" style="font-size:11px">${__('baris')}</span>
    </div>
  `;
  $controls.html(controlHtml);

  function load(limit = 20) {
    $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

    frappe.call({
      method: 'tekma_app.api.get_item_price_history',
      args: {
        company,
        item_code,
        customer: customer || undefined,
        limit
      },
      callback: (r) => {
        const data = (r && r.message) ? r.message : {};
        const rows = data.rows || [];
        const currency = frm.doc.currency || frappe.defaults.get_default('currency') || 'IDR';
        const fmt = (v) => format_currency(v || 0, currency);

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
          <div class="mt-2 text-muted">${__('Baris ditampilkan')}: ${rows.length} • ${__('Batas')}: ${limit}</div>
        `;

        $wrap.html(body_html);
      },
      error: () => {
        $wrap.html(`<div class="text-danger">${__('Gagal memuat data.')}</div>`);
      }
    });
  }

  // Hook change to reload data with selected limit
  $controls.find('select[data-role="page-size"]').on('change', function () {
    const val = parseInt($(this).val(), 10) || 20;
    load(val);
  });

  // Initial load with default 20
  load(20);
}

function open_tiang_history_dialog(frm) {
  const { customer } = frm.doc || {};
  if (!customer) {
    frappe.msgprint({ message: __('Customer belum dipilih.'), indicator: 'orange' });
    return;
  }

  const d = new frappe.ui.Dialog({
    title: __('History Tiang • {0}', [frappe.utils.escape_html(customer)]),
    size: 'large',
    fields: [
      { fieldtype: 'HTML', fieldname: 'controls_html' },
      { fieldtype: 'HTML', fieldname: 'body_html' }
    ],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();
  try { d.$wrapper.find('.modal-dialog').css({ 'max-width': '1200px', 'width': '95%' }); } catch (e) {}

  const $controls = d.get_field('controls_html').$wrapper;
  const $wrap = d.get_field('body_html').$wrapper;

  const controlHtml = `
    <div style="display:flex;justify-content:space-between;gap:8px;margin-bottom:6px;align-items:center">
      <div class="text-muted" style="font-size:11px">${__('Menampilkan riwayat dari Doctype')} <b>History Tiang</b></div>
      <div style="display:flex;gap:8px;align-items:center">
        <span class="text-muted" style="font-size:11px">${__('Tampilkan')}</span>
        <select class="form-control input-sm" style="width:auto" data-role="page-size">
          <option value="20" selected>20</option>
          <option value="50">50</option>
          <option value="100">100</option>
          <option value="500">500</option>
        </select>
        <span class="text-muted" style="font-size:11px">${__('baris')}</span>
      </div>
    </div>
  `;
  $controls.html(controlHtml);

  async function load(limit = 20) {
    $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

    try {
      const rows = await frappe.db.get_list('History Tiang', {
        filters: { customer },
        fields: ['name', 'posting_date', 'document_type', 'document', 'qty', 'docstatus'],
        order_by: 'posting_date desc, creation desc',
        limit: limit
      });

      const style = `
        <style>
          .tiang-dialog { font-size: 12px; }
          .tiang-dialog table.table th, .tiang-dialog table.table td { padding: 4px 8px; vertical-align: middle; }
          .muted { color: #6b7280; font-size: 11px; }
        </style>
      `;

      const header = `
        <thead>
          <tr>
            <th style="text-align:center;width:50px">No</th>
            <th style="text-align:left;width:200px">${__('Tanggal')}</th>
            <th style="text-align:left;width:140px">${__('Document Type')}</th>
            <th style="text-align:left">${__('Document')}</th>
            <th style="text-align:right;width:100px">${__('Qty')}</th>
            <th style="text-align:center;width:90px">${__('Status')}</th>
          </tr>
        </thead>
      `;

      let body_rows = '';
      rows.forEach((r, i) => {
        const dt = r.document_type || '';
        const dn = r.document || '';
        const route_dt = (dt || '').toLowerCase().replace(/\s+/g, '-');
        const doc_link = (dt && dn)
          ? `<a href="/app/${route_dt}/${encodeURIComponent(dn)}" target="_blank" rel="noopener">${frappe.utils.escape_html(dn)}</a>`
          : '<span class="muted">-</span>';
        const status = r.docstatus === 1 ? __('Submitted') : (r.docstatus === 2 ? __('Cancelled') : __('Draft'));
        body_rows += `
          <tr>
            <td style="text-align:center">${i + 1}</td>
            <td>${frappe.datetime.str_to_user(r.posting_date)}</td>
            <td>${frappe.utils.escape_html(dt)}</td>
            <td>${doc_link}</td>
            <td style="text-align:right">${frappe.format(r.qty || 0, { fieldtype: 'Float' })}</td>
            <td style="text-align:center">${status}</td>
          </tr>
        `;
      });

      const html = `
        ${style}
        <div class="tiang-dialog" style="overflow:auto; max-height:70vh">
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${header}
            <tbody>
              ${body_rows || `<tr><td colspan="6" style="text-align:center; color:#888">${__('Tidak ada data')}</td></tr>`}
            </tbody>
          </table>
        </div>
        <div class="mt-2 text-muted">${__('Baris ditampilkan')}: ${rows.length} • ${__('Batas')}: ${limit}</div>
      `;

      $wrap.html(html);
    } catch (err) {
      console.error(err);
      $wrap.html(`<div class="text-danger">${__('Gagal memuat data.')}</div>`);
    }
  }

  $controls.find('select[data-role="page-size"]').on('change', function () {
    const val = parseInt($(this).val(), 10) || 20;
    load(val);
  });

  load(20);
}
