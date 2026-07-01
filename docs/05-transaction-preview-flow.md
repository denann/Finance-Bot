# 05. Transaction & Preview Flow

Bagian ini menjelaskan bagaimana bot memastikan data tidak langsung tersimpan tanpa dicek user.

File utama:

```text
app/bot/handler_parts/message_handlers.py
app/bot/handler_parts/transaction_flow.py
app/bot/handler_parts/callback_handler.py
```

## Alur input teks biasa

Secara umum:

```text
message_handler()
→ handle local natural intent jika cocok
→ split_user_inputs()
→ parse tiap item
→ assess_parse_safety()
→ preview / warning / clarification
→ user tekan tombol
→ callback_handler()
→ save via service layer
```

## Kenapa ada preview?

Preview mencegah kesalahan parsing langsung tersimpan ke Google Sheets.

Tombol umum:

```text
Edit dulu
Lanjut
Batal
```

Setelah user menekan `Lanjut`, bot bisa lanjut ke:

- pilih rekening,
- preview final,
- konfirmasi simpan,
- debt flow,
- split bill decision,
- pending expense confirmation.

## Normal preview

Dipakai jika parsing aman.

Contoh input:

```text
beli kopi 20k dari Cash
```

Alur:

```text
parse sukses
→ normal_preview
→ tampil preview existing
→ Edit dulu / Lanjut / Batal
```

## Warning preview

Dipakai jika parser mungkin benar tapi rawan salah.

Contoh:

```text
makanan ikan 10k
```

Alur:

```text
parse sukses, tapi category_uncertain
→ warning_preview
→ tampil warning + alasan
→ tampil preview existing
→ Edit dulu / Lanjut / Batal
```

## Gemini draft preview

Dipakai untuk case non-sensitive saat Gemini bisa membantu membuat draft.

Alur:

```text
parse safety merekomendasikan Gemini draft
→ coba Gemini draft
→ hasil Gemini tetap masuk preview warning
→ user tetap bisa edit/batal
```

Artinya Gemini tidak menyimpan data langsung.

## Clarification flow

Dipakai jika input terlalu ambigu.

Contoh:

```text
Budi bayar makan 100k
```

Bot akan bertanya:

```text
Maksudnya yang mana?
1. Budi bayar hutang/piutang ke saya
2. Saya mencatat pengeluaran makan Rp100.000
3. Budi yang membayar, tidak perlu mengubah saldo saya
4. Saya talangin Budi
5. Saya tulis ulang inputnya
```

Pilihan user diproses di `callback_handler.py`, lalu diarahkan ke flow existing.

## Edit flow

Edit flow berada di `transaction_flow.py`.

Konsepnya:

```text
preview awal
→ user pilih Edit dulu
→ bot tampilkan format edit
→ user kirim perubahan
→ parsed dict diperbarui
→ preview ulang
```

Field yang bisa diedit tergantung jenis item, misalnya:

- amount,
- category,
- account,
- description,
- subject,
- date,
- tipe_pengeluaran,
- debt person,
- asset field.

## Mixed transaction

Bot mendukung input banyak item dalam satu pesan.

Contoh:

```text
beli kopi 20k dari Cash, Budi minjem 50k, gaji masuk 8jt ke BCA
```

Alur:

```text
split_user_inputs()
→ parse_mixed_item()
→ build_mixed_preview()
→ edit/continue/cancel
→ save batch
```

Mixed item bisa berisi:

- transaction,
- debt,
- pending expense,
- split bill.

## Split bill flow

Split bill tidak langsung save.

Alur high level:

```text
input split bill
→ parser mendeteksi split info
→ tanya status teman sudah bayar atau belum jika perlu
→ preview
→ Edit dulu / Lanjut / Batal
→ pilih rekening jika perlu
→ Simpan / Batal
```

Contoh pola yang didukung:

```text
galon 24k dibagi 4
makan 80k bagi dua sama Budi
makan 80k berdua sama Budi
minyak 46k patungan berempat sama Budi Rina Tono
```

## Debt flow

Debt flow juga harus melewati preview awal.

Contoh:

```text
Budi minjem 50k
```

Alur:

```text
parse_debt_input()
→ preview debt awal
→ Edit dulu / Lanjut / Batal
→ jika lanjut, pilih rekening / konfirmasi final
→ Simpan / Batal
```

Tujuannya agar hutang/piutang tidak langsung membuat cashflow tanpa cek user.

## Pending expense flow

Pending expense digunakan untuk rencana transaksi atau tagihan masa depan.

Contoh:

```text
nanti bayar wisuda 750k pakai BSI
wifi bulan depan 285k
```

Flow:

```text
pending detected
→ preview pending
→ Edit dulu / Lanjut / Batal
→ Simpan / Batal
```

## Asset/net worth flow

Aset dan net worth juga menggunakan preview sebelum save.

Alur:

```text
asset input
→ parse asset
→ preview
→ Edit dulu / Lanjut / Batal
→ Simpan / Batal
```

## Final save

Final save dilakukan di service layer, bukan di parser.

Contoh service yang dipakai:

- `save_transaction()`
- `save_transactions_batch()`
- `add_debt()`
- `add_payment()`
- `save_pending_expense()`
- `add_asset()`
- `add_liability()`

Semua handler dibungkus `sheets_transaction()` supaya write ke Google Sheets lebih aman.
