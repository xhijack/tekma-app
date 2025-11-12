frappe.ui.form.on('Purchase Invoice', {

  refresh(frm) {
    // Tampilkan tombol hanya jika ada hutang outstanding
    if (!frm._ap_loading && Number(frm.doc.current_outstanding || 0) > 0) {
      frm.add_custom_button(__('Lihat Hutang'), () => open_ap_dialog(frm));
    }
    if (frm.doc.supplier) {
      frm.add_custom_button(__('History Tiang'), () => open_tiang_history_dialog(frm));
    }
  },

  supplier(frm) {
    frm._ap_loading = true;
    fetch_ap_summary(frm);
  },

  company(frm) {
    frm._ap_loading = true;
    fetch_ap_summary(frm);
  },
});

function fetch_ap_summary(frm) {
  const { supplier, company } = frm.doc || {};
  if (!supplier || !company) {
    frm._ap_loading = false;
    return;
  }

  frappe.call({
    method: 'tekma_app.api.get_ap_summary_by_supplier',
    args: { company, supplier },
    callback: (r) => {
      const data = (r && r.message) ? r.message : {};
      const outstanding = data.outstanding_amount || 0;
      // set_value memicu refresh -> tombol muncul di refresh
      frm.set_value('current_outstanding', outstanding);
      frm._ap_loading = false;
    },
    error: () => {
      frm._ap_loading = false;
    }
  });
}

function open_ap_dialog(frm) {
  const { company, supplier } = frm.doc || {};
  if (!company || !supplier) return;

  const d = new frappe.ui.Dialog({
    title: __('Daftar Hutang (AP)'),
    size: 'large',
    fields: [{ fieldtype: 'HTML', fieldname: 'ap_html' }],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();
  try { d.$wrapper.find('.modal-dialog').css({ 'max-width': '1400px', 'width': '95%' }); } catch (e) {}

  const $wrap = d.get_field('ap_html').$wrapper;
  $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

  frappe.call({
    method: 'tekma_app.api.get_ap_invoices_by_supplier',
    args: { company, supplier },
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
        net_payable: 0
      };

      const fmt = (v) => format_currency(v || 0, currency);

      const style = `
        <style>
          .ap-dialog { font-size: 12px; }
          .ap-dialog table.table th,
          .ap-dialog table.table td { padding: 4px 8px; vertical-align: middle; }
          .ap-section-title { margin: 8px 0; font-weight: 600; }
          .ap-summary .row { display: flex; gap: 16px; flex-wrap: wrap; }
          .ap-summary .box { padding: 8px 12px; border: 1px solid #e5e7eb; border-radius: 6px; background: #fafafa; }
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
            <td><a href="/app/purchase-invoice/${encodeURIComponent(inv.name)}" target="_blank" rel="noopener">${frappe.utils.escape_html(inv.name)}</a></td>
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

      // Credit Notes (Remaining)
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
          ? `<a href="/app/purchase-invoice/${encodeURIComponent(cn.return_against)}" target="_blank" rel="noopener">${frappe.utils.escape_html(cn.return_against)}</a>`
          : `<span class="muted">-</span>`;
        cn_rows += `
          <tr>
            <td style="text-align:center">${idx + 1}</td>
            <td>${frappe.datetime.str_to_user(cn.posting_date)}</td>
            <td><a href="/app/purchase-invoice/${encodeURIComponent(cn.name)}" target="_blank" rel="noopener">${frappe.utils.escape_html(cn.name)}</a></td>
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
        <div class="ap-summary" style="margin-top:8px;">
          <div class="row">
            <div class="box">${__('Invoices Outstanding (Adjusted)')}: <b>${fmt(x.invoices_outstanding_adjusted)}</b></div>
            <div class="box">${__('Credit Note Available (Remaining)')}: <b>${fmt(x.credit_note_available)}</b></div>
            <div class="box">${__('Advance (Unallocated)')}: <b>${fmt(x.advance_unallocated)}</b></div>
            <div class="box">${__('Net Payable')}: <b>${fmt(x.net_payable)}</b></div>
          </div>
        </div>
      `;

      const html = `
        ${style}
        <div class="ap-dialog" style="overflow:auto; max-height:72vh">
          <div class="ap-section-title">${__('Purchase Invoices (Outstanding, Adjusted with Returns)')}</div>
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${inv_header}
            <tbody>
              ${inv_rows || `<tr><td colspan="7" style="text-align:center; color:#888">${__('Tidak ada data')}</td></tr>`}
              ${inv_rows ? inv_totals : ''}
            </tbody>
          </table>

          <div class="ap-section-title">${__('Credit Notes (Remaining)')}</div>
          <table class="table table-bordered" style="width:100%; background:#fff">
            ${cn_header}
            <tbody>
              ${cn_rows || `<tr><td colspan="5" style="text-align:center; color:#888">${__('Tidak ada credit note tersedia')}</td></tr>`}
            </tbody>
          </table>

          <div class="ap-section-title">${__('Advances / Dana Menggantung')}</div>
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


frappe.ui.form.on('Purchase Invoice Item', {
  check_price(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row || !row.item_code) {
      frappe.msgprint({ message: __('Pilih Item terlebih dahulu.'), indicator: 'orange' });
      return;
    }
    open_item_cost_dialog(frm, row);
  }
});

function open_item_cost_dialog(frm, row) {
  const { company, supplier } = frm.doc || {};
  if (!company) {
    frappe.msgprint({ message: __('Company belum dipilih.'), indicator: 'orange' });
    return;
  }
  if (!row?.item_code) {
    frappe.msgprint({ message: __('Pilih Item terlebih dahulu.'), indicator: 'orange' });
    return;
  }

  const d = new frappe.ui.Dialog({
    title: __('Riwayat Harga Beli • {0}', [frappe.utils.escape_html(row.item_code)]),
    size: 'large',
    fields: [{ fieldtype: 'HTML', fieldname: 'price_html' }],
    primary_action_label: __('Tutup'),
    primary_action() { d.hide(); },
  });

  d.show();
  try { d.$wrapper.find('.modal-dialog').css({ 'max-width': '1200px', 'width': '95%' }); } catch (e) {}

  const $wrap = d.get_field('price_html').$wrapper;
  $wrap.html(`<div class="text-muted">${__('Memuat data...')}</div>`);

  frappe.call({
    method: 'tekma_app.api.get_item_cost_history',
    args: {
      company,
      item_code: row.item_code,
      supplier: supplier || undefined,
      limit: 100
    },
    callback: (r) => {
      const data = (r && r.message) ? r.message : {};
      const rows = data.rows || [];
      const currency = frm.doc.currency || frappe.defaults.get_default('currency') || 'IDR';
      const fmt = (v) => format_currency(v || 0, currency);

      const style = `
        <style>
          .po-price-dialog { font-size: 12px; }
          .po-price-dialog table.table th,
          .po-price-dialog table.table td { padding: 4px 8px; vertical-align: middle; }
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
              <a href="/app/purchase-invoice/${encodeURIComponent(it.invoice)}" target="_blank" rel="noopener">
                ${frappe.utils.escape_html(it.invoice)}
              </a>
            </td>
            <td style="text-align:right">${frappe.format(it.qty, {fieldtype: 'Float'})}</td>
            <td>${frappe.utils.escape_html(it.uom || '')}</td>
            <td style="text-align:right">${fmt(it.rate)}</td>
            <td style="text-align:right"><b>${fmt(it.net_amount)}</b></td>
          </tr>
        `;
      });

      const body_html = `
        ${style}
        <div class="po-price-dialog" style="overflow:auto; max-height:70vh">
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



function open_tiang_history_dialog(frm) {
  const { supplier } = frm.doc || {};
  if (!supplier) {
    frappe.msgprint({ message: __('Supplier belum dipilih.'), indicator: 'orange' });
    return;
  }

  const d = new frappe.ui.Dialog({
    title: __('History Tiang • {0}', [frappe.utils.escape_html(supplier)]),
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
      
      // Coba dapatkan Customer yang terkait dengan Supplier lewat Party Link
      let customerFilter = supplier;
      try {
        const party_links = await frappe.db.get_list('Party Link', {
          filters: { primary_role: 'Supplier', primary_party: supplier },
          fields: ['secondary_party'],
          limit: 0
        });

        const customers = (party_links || [])
          .filter(pl => (pl.link_doctype || '').toLowerCase() === 'customer')
          .map(pl => pl.secondary_party);

        if (customers.length) {
          // gunakan filter IN jika ada lebih dari satu customer terkait
          customerFilter = ['in', customers];
        }
      } catch (e) {
        console.error('Gagal mengambil Party Link:', e);
      }
      // alert('customerFilter: ' + JSON.stringify(customerFilter));

      const rows = await frappe.db.get_list('History Tiang', {
        filters: { customer: customerFilter },
        fields: ['name', 'posting_date', 'document_type', 'document', 'qty','condition','rate','docstatus'],
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
            <th style="text-align:right;width:100px">${__('Condition')}</th>
            <th style="text-align:right;width:100px">${__('Rate')}</th>
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
            <td style="text-align:center">${r.condition}</td>
            <td style="text-align:center">${frappe.format(r.rate || 0, { fieldtype: 'Currency' })}</td>
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
