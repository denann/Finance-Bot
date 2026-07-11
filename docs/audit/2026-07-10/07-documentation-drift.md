# Documentation Drift Audit

Tanggal audit: 2026-07-10

Status yang dipakai: `CURRENT`, `PARTIALLY_OBSOLETE`, `OBSOLETE`, `MISSING`, `MISLEADING`, `DUPLICATED`.

Skill dokumentasi inti digunakan untuk memeriksa README, manual, dokumen arsitektur/flow, dan dokumentasi folder secara sistematis. Tidak ada existing documentation yang diubah dalam audit ini.

## Inventory dan status

| Dokumen | Status | Bukti drift / catatan | Rekomendasi setelah approval |
|---|---|---|---|
| Root `README.md` | `PARTIALLY_OBSOLETE` | cakupan fitur luas, tetapi dependency/runtime, protected preview contract, single-instance, dan known limitations tidak cukup eksplisit | sinkronkan command registry, setup, safety, dan deployment invariant |
| `docs/README.md` | `PARTIALLY_OBSOLETE` | indeks ada tetapi tidak membedakan current source of truth vs historical/reference docs | beri status/owner/last-verified per dokumen |
| `docs/01-project-overview.md` | `PARTIALLY_OBSOLETE` | high-level masih relevan; detail capability dan operational constraint tertinggal | tautkan system map aktual dan single-user boundary |
| `docs/02-architecture.md` | `PARTIALLY_OBSOLETE` | belum mencerminkan monolith handler, import cycle, atomic wrapper limit, scheduler ownership | perbarui setelah Phase 0 contract diputuskan |
| `docs/03-data-model.md` | `PARTIALLY_OBSOLETE` | schema overview tidak cukup menjelaskan absence of tenant/idempotency/audit keys | tambahkan invariants dan migration policy tanpa mengubah schema |
| `docs/04-user-flows.md` | `MISLEADING` | menggambarkan flow lebih seragam daripada implementasi command/callback aktual | beri matriks per command dan tandai direct-write flow |
| `docs/05-safety-and-confirmation.md` | `MISLEADING` | klaim/implikasi universal preview-before-write tidak benar untuk beberapa pending/recurring/asset action | jangan revisi klaim sampai behavior diperbaiki/owner memutuskan |
| `docs/06-google-sheets.md` | `PARTIALLY_OBSOLETE` | schema dasar berguna; retry/idempotency, atomicity limit, quota, sort/rewrite cost tidak lengkap | dokumentasikan failure semantics dan staging rules |
| `docs/07-ai-and-gemini.md` | `PARTIALLY_OBSOLETE` | model default/example drift; timeout, output/token cap, redaction, prompt version, cost metrics tidak ada | tetapkan model/config contract dan privacy policy |
| `docs/08-configuration-and-deployment.md` | `MISLEADING` | readiness, process count, scheduler ownership, hidden retry env, clean-install reproducibility belum tercakup | tambahkan single-process constraint dan readiness checklist |
| `docs/09-function-reference.md` | `DUPLICATED` | section/path seperti `app/app/...` dan current sections berulang; mudah drift dari code | generate dari AST atau ringkas ke stable public surfaces |
| `docs/10-maintenance.md` | `CURRENT` | prinsip maintenance masih berguna, tetapi belum memiliki CI/test/observability gate | perluas setelah test foundation tersedia |
| `docs/help_manual.md` | `MISLEADING` | user-facing preview/write semantics dan command availability tidak seluruhnya sama dengan registry/implementation | jadikan registry+flow tests sebagai source sebelum regenerate |
| `docs/help_manual.pdf` | `PARTIALLY_OBSOLETE` | artifact turunan mewarisi drift Markdown dan tidak terbukti diregenerate dari commit ini | regenerate dan visual-QA hanya setelah source disetujui |
| `app/README.md` | `PARTIALLY_OBSOLETE` | module map belum menunjukkan hotspot/import cycle dan actual ownership | ringkas boundary, jangan duplikasi function reference |
| `app/bot/README.md` | `PARTIALLY_OBSOLETE` | callback/state/atomic wrapper limitations tidak terlihat | dokumentasikan state lifecycle dan routing order |
| `app/handlers/README.md` | `PARTIALLY_OBSOLETE` | file besar/command ownership dan direct-write exceptions tidak jelas | daftar public handlers dari registry otomatis |
| `app/services/README.md` | `PARTIALLY_OBSOLETE` | service return-vs-exception atomicity contract tidak didefinisikan | tetapkan service result/error contract |
| `app/sheets/README.md` | `PARTIALLY_OBSOLETE` | operasi dasar relevan; retry non-idempotent dan transaction boundary tidak terdokumentasi | tambah safe retry matrix |
| `app/scripts/README.md` | `PARTIALLY_OBSOLETE` | duplicate tester dan dependency/staging assumptions tidak jelas | pilih canonical CLI dan nyatakan read/write behavior |
| `scripts/README.md` | `DUPLICATED` | overlap dengan `app/scripts` tanpa canonical ownership | pertahankan wrapper atau konsolidasikan setelah tests |
| Dedicated testing guide | `MISSING` | tidak ada cara resmi menjalankan deterministic suite/staging smoke | buat `docs/testing.md` saat tests tersedia |
| Operational runbook | `MISSING` | tidak ada readiness, rollback, scheduler, incident/reconciliation runbook lengkap | buat deployment/runbook setelah Phase 0–1 |
| Architecture walkthrough | `MISSING` | fungsi tersebar di file besar; onboarding bergantung pada function dump | tulis stable end-to-end flows, bukan line-by-line catalog |

## Drift antar source of truth

- Command registry, help manual, tester known-command list, dan dead liability handlers tidak sepakat.
- Contoh/default model Gemini tidak konsisten antara code dan dokumentasi.
- Dokumentasi menyatakan safety flow lebih universal daripada implementasinya.
- Function reference menggandakan section sehingga “current” tidak jelas.
- Environment examples tidak memuat seluruh runtime knobs Sheets retry.

## Urutan sinkronisasi yang aman

1. Owner memutuskan callback, confirmation, retry, dan unavailable liability contracts.
2. Tambah contract tests terhadap command registry dan flow.
3. Perbaiki implementation pada phase terpisah.
4. Update manual/README dari behavior yang sudah teruji.
5. Regenerate PDF dan function inventory; lakukan link/visual check.

Memperbarui docs sebelum behavior diputuskan akan memperkuat kontradiksi, bukan menyelesaikannya.
