# Dokumentasi Sintaks Denan Finance Bot

Dokumentasi ini dibuat untuk membantu memahami **maksud kode**, bukan sekadar daftar file. Urutan bacanya dibuat dari level besar ke detail teknis.

## Cara membaca dokumentasi ini

1. Mulai dari [01 Project Map](01-project-map.md) untuk memahami gambaran folder dan tanggung jawab tiap layer.
2. Lanjut ke [02 Runtime & Entrypoint](02-runtime-entrypoint.md) untuk memahami bagaimana bot dijalankan.
3. Baca [03 Telegram Bot Flow](03-telegram-bot-flow.md) untuk memahami bagaimana pesan Telegram masuk ke handler.
4. Baca [04 Parser, NLP, dan Parse Safety](04-parser-nlp-parse-safety.md) untuk memahami alur parsing input natural language.
5. Baca [05 Transaction & Preview Flow](05-transaction-preview-flow.md) untuk memahami kenapa data tidak langsung disimpan.
6. Baca [06 Data Layer & Services](06-data-layer-services.md) untuk memahami Google Sheets, atomic write, dan service layer.
7. Baca [07 AI Insight Layer](07-ai-insight-layer.md) untuk memahami fitur `/ask`, `/audit`, `/coach`, dan `/insight`.
8. Baca [08 Setup, Debugging, dan Deployment](08-setup-debug-deployment.md) untuk memahami script operasional.
9. Gunakan [09 Function Reference](09-function-reference.md) sebagai indeks fungsi per file.
10. Gunakan [10 Glossary](10-glossary.md) untuk istilah penting dalam project.

## Prinsip dokumentasi

Dokumentasi ini dibagi menjadi:

- **Explanation**: menjelaskan alasan desain dan mental model.
- **How-to**: menjelaskan langkah menjalankan atau men-debug.
- **Reference**: daftar file, fungsi, dan tanggung jawab teknis.

Fokus utamanya adalah membantu developer baru memahami alur berpikir kode: dari input Telegram sampai data tersimpan di Google Sheets.
