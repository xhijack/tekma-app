# Realized Profit — ERPNext v15

Script Report ringkasan bulanan berdasarkan **Fiscal Year**.

## Kolom

- Month
- Income
- Expense
- Actual Receipt
- Collection Ratio
- Accounting Profit
- Realized Profit
- Real vs Accounting %
- Outstanding Invoice

`Outstanding Invoice` dapat diklik untuk membuka **Sales Invoice List** yang sudah difilter berdasarkan:

- Company report
- Posting Date bulan terkait
- Submitted
- Bukan Sales Return
- Outstanding Amount lebih dari 0

## Rumus

```text
Collection Ratio         = Actual Receipt / Income
Accounting Profit          = Income - Expense
Realized Profit            = Actual Receipt - Expense
Real vs Accounting %       = Realized Profit / Accounting Profit × 100
```

Collection Ratio dapat melebihi 100% apabila penerimaan bulan tersebut mencakup pembayaran invoice bulan sebelumnya.

## Sumber data

### Income dan Expense

Dibaca dari `GL Entry` berdasarkan COA:

- Income = Credit - Debit untuk akun `root_type = Income`
- Expense = Debit - Credit untuk akun `root_type = Expense`
- Period Closing Voucher tidak dihitung

Expense mencakup COGS dan seluruh operating expense yang masuk Profit and Loss.

### Actual Receipt

Uang pelanggan yang benar-benar masuk atau keluar dari akun Cash/Bank:

- Payment Entry Customer: Receive dikurangi Pay/refund
- POS Invoice
- Sales Invoice POS langsung yang bukan consolidated
- Journal Entry yang memiliki baris Customer dan baris Cash/Bank

Credit Note dan write-off tanpa perpindahan kas tidak dihitung sebagai Actual Receipt.

### Outstanding Invoice

Nilai outstanding **saat report dijalankan** untuk Sales Invoice yang tanggal postingnya berada pada bulan tersebut. Nilai dikonversi ke company currency memakai conversion rate invoice.

## Instalasi

Salin folder `realized_profit` ke custom app:

```text
apps/tekma_app/tekma_app/tekma_app/report/realized_profit/
```

Kemudian:

```bash
bench --site nama-site migrate
bench --site nama-site clear-cache
bench restart
```


## Keamanan transaksi POS

- `POS Invoice` ERPNext v15 dihitung langsung dari `base_paid_amount - base_change_amount`.
- `Sales Invoice` dengan `is_pos = 1` hanya dipakai untuk kompatibilitas transaksi POS legacy.
- Sales Invoice hasil konsolidasi (`is_consolidated = 1`) tidak dihitung agar kas POS tidak terhitung dua kali.
- POS return dihitung sebagai penerimaan negatif.
- Warna Accounting Profit hijau jika laba dan merah jika rugi.
- Warna Realized Profit dan Real vs Accounting % hijau jika Realized Profit minimal sama dengan Accounting Profit; selain itu merah.
