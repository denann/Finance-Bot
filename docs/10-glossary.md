# 10. Glossary

## Account

Rekening/sumber dana user, misalnya `Cash`, `BRI`, `BCA`, `DANA`, `GoPay`.

## Amount

Nominal transaksi dalam rupiah. Input seperti `20k`, `1.2jt`, atau `2 juta` akan dinormalisasi menjadi angka.

## Atomic write

Pola write Google Sheets yang berusaha memastikan beberapa perubahan data diperlakukan sebagai satu operasi. Jika salah satu gagal, sistem mencoba rollback perubahan sebelumnya.

## Callback

Event dari tombol inline Telegram. Contoh: user menekan `Lanjut`, `Batal`, `Simpan`, atau memilih rekening.

## Clarification

Flow ketika bot belum yakin maksud input user. Bot bertanya dulu sebelum preview atau save.

## Debt

Hutang/piutang personal. Di project ini debt bisa berupa `payable` atau `receivable`.

## Ditalangin

Kondisi ketika orang lain membayar dulu untuk user. Biasanya membuat user punya utang ke orang tersebut.

## Gemini draft preview

Preview yang dibantu Gemini untuk input non-sensitive. Hasilnya tetap harus dicek user dan tidak langsung disimpan.

## Handler

Fungsi yang menerima update Telegram, misalnya command, pesan teks, foto, atau callback button.

## Operational data store

Tempat data operasional disimpan. Di project ini menggunakan Google Sheets.

## Parse safety routing

Layer yang menilai apakah hasil parsing aman atau perlu warning/klarifikasi.

## Pending expense

Rencana/tagihan yang belum tentu sudah dibayar. Disimpan sebagai pending agar tidak langsung mengubah saldo.

## Polling mode

Mode runtime di mana bot mengambil update dari Telegram secara berkala. Ini mode default project.

## Preview before write

Prinsip bahwa data harus ditampilkan dulu ke user sebelum disimpan ke Google Sheets.

## Receivable / Piutang

Orang lain berutang kepada user.

## Payable / Utang

User berutang kepada orang lain.

## Service layer

Layer yang menyimpan business logic finansial, misalnya save transaksi, update saldo, settle debt, hitung budget.

## Split bill

Transaksi yang dibagi dengan orang lain. Bot bisa membuat piutang/utang terkait pembagian tersebut.

## Talangin

Kondisi ketika user membayar dulu untuk orang lain. Biasanya membuat orang lain punya utang ke user.

## Warning preview

Preview dengan peringatan karena hasil parser mungkin rawan salah.

## Webhook mode

Mode runtime advanced di mana Telegram mengirim update ke endpoint FastAPI.
