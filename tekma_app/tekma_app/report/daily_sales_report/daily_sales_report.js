frappe.query_reports["Daily Sales Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "date",
            "label": __("Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
    ],
    onload: function(report) {
        report.page.set_primary_action(__('Custom Print'), function() {
            let filters = report.get_values();

            frappe.call({
                method: 'frappe.desk.query_report.run',
                args: {
                    report_name: 'Daily Sales Report',
                    filters: filters
                },
                callback: function(r) {
                    if(r.message) {
                        let columns = r.message.columns;
                        let data = r.message.result;
                        let totalTunai = 0, totalBank = 0, totalPiutang = 0, totalJumlah = 0;
                        let filteredData = data.filter(row => {
                            return (row['tunai'] || row['bank'] || row['piutang'] || row['jumlah'] || row['no_faktur']);
                        });

                        data.forEach(row => {
                            totalTunai += row['tunai'] || 0;
                            totalBank += row['bank'] || 0;
                            totalPiutang += row['piutang'] || 0;
                            totalJumlah += row['jumlah'] || 0;
                        });

                        let printDateTime = getFormattedDateTime();

                        let print_html = `
                        <style>
                            @page {
                                size: A4 portrait;
                                margin: 10mm;
                            }
                            @media print {
                                td, th {
                                    -webkit-print-color-adjust: exact;
                                    print-color-adjust: exact;
                                }

                                body {
                                    counter-reset: page; 
                                }
                                
                                .page-number:after {
                                    counter-increment: page;
                                    content: "[P." counter(page) "]";
                                }

                            }

                            body {
                                font-family: Arial, sans-serif;
                                text-align: center;
                            }
                            h3 {
                                margin-bottom: 10px;
                            }
                            table {
                                border-collapse: collapse;
                                width: 100%;
                                margin: 0 auto;
                                text-align: left;
                            }
                            th, td {
                                border: 1px solid #000;
                                padding: 4px;
                                font-size: 11px;
                            }
                            th {
                                text-align:center;
                            }
                            td.currency {
                                text-align: right;
                            }
                        </style>

                        <h3>Pemasukkan Harian ${formatDate(filters.date)}</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th style="background-color: #f0f0f0;">No</th>
                                    ${columns.map(c => `<th style="background-color: #f0f0f0; ${["Tunai", "Bank"].includes(c.label)? "width: 11%;": c.label =="Jumlah"?"width: 13%;": ""}">${c.label}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${filteredData.map((row, index)=> `<tr>
                                    <td style="text-align:right;">${index + 1}</td> 
                                    ${columns.map(c => {
                                        if (c.label === "Tgl" && row.tgl) {
                                            const d = new Date(row.tgl);
                                            const day = String(d.getDate()).padStart(2, '0');
                                            const month = String(d.getMonth() + 1).padStart(2, '0');
                                            return `<td>${day}/${month}</td>`;
                                        } else if(c.label.match(/Tunai|Bank|Piutang|Jumlah/)) {
                                            return `<td class="currency">${formatCurrency(row[c.fieldname])}</td>`;
                                        } else if(c.label == "Instansi"){
                                            return `<td>${row[c.fieldname]?.substring(0, 15) || ''}</td>`
                                        } else {
                                            return `<td>${row[c.fieldname] || ''}</td>`;
                                        }
                                    }).join('')}
                                </tr>`).join('')}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="5" style="text-align:right; font-size:12px;"><b>Jumlah Keseluruhan:</b></td>
                                    <td style="font-size:12px; background-color: #f0f0f0;" class="currency"><b>${formatCurrency(totalTunai)}</b></td>
                                    <td style="font-size:12px; background-color: #f0f0f0;" class="currency"><b>${formatCurrency(totalBank)}</b></td>
                                    <td style="font-size:12px; background-color: #f0f0f0;" class="currency"><b>${formatCurrency(totalPiutang)}</b></td>
                                    <td style="font-size:12px; background-color: #f0f0f0;" class="currency"><b>${formatCurrency(totalJumlah)}</b></td>
                                </tr>
                            </tfoot>
                        </table>

                        <div style="width:100%; display:flex; justify-content:space-between; font-size:11px; margin-top:4px; gap: 100px; margin-top:10px;">
                            <div width="50%">
                                <table width="100%">
                                    <thead>
                                        <th width="120px">Pelanggan</th>
                                        <th width="150px">AR Rp</th>
                                        <th width="50px">PE ✍️</th>
                                    </thead>
                                    <tbody>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                        <tr><td style="padding:3px;">&nbsp;</td><td></td><td></td></tr>
                                    </tbody>
                                </table>
                            </div>
                            <div width="50%">
                                <div style="float: left;">Cetak: ${printDateTime}</div>
                                <div style="float: right;" class="page-number"></div>
                                <table width="100%" style="margin-top: 17px">
                                    <tbody>
                                        <tr>
                                            <td align="center" colspan="2">Setoran Tunai</td>
                                        </tr>
                                        <tr>
                                            <td align="center" colspan="2" style="height: 35px"></td>
                                        </tr>
                                        <tr>
                                            <td align="center">Petty Form</td>
                                            <td align="center">Daily Cost From</td>
                                        </tr>
                                        <tr>
                                            <td style="height: 40px; width: 50%;"></td>
                                            <td style="height: 40px; width: 50%;"></td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        `;

                        let w = window.open();
                        w.document.write(print_html);
                        w.document.close();
                        w.print();
                    }
                }
            });
        });

    }
};

function getFormattedDateTime() {
    const now = new Date();
    const days =["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
    const dayName = days[now.getDay()];

    const dd = String (now.getDate()).padStart(2, '0');
    const mm = String (now.getMonth() + 1).padStart(2, '0');
    const yyyy = now.getFullYear();

    const hh = String(now.getHours()).padStart(2, '0');
    const min = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');

    return `${dd}/${mm}/${yyyy} (${dayName}) ${hh}:${min}:${ss}`
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const dd = String(d.getDate()).padStart(2, '0');
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const yyyy = d.getFullYear();
    return `${dd}/${mm}/${yyyy}`;
}

function formatCurrency(amount) {
    if (!amount) return "";
    return Number(amount). toLocaleString("id-ID", {minimumFractionDigits: 0})
}
