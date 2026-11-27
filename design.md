# DESIGN.md — FinEduSearch (arah visual: "Calm Data")

Dokumen ini adalah spesifikasi design system untuk antarmuka **FinEduSearch**. Baca seluruhnya sebelum mengubah kode, lalu kerjakan sesuai bagian **12. Rencana implementasi**.

---

## 0. Aturan kerja untuk agen

1. **Hanya ubah lapisan tampilan:** `templates/index.html`, `static/style.css`, `static/script.js`, dan file CSS baru di `static/`.
2. **Jangan ubah** `app.py`, `indexer.py`, `preprocessor.py`, `crawler.py`, `evaluator.py`, isi folder `data/`, maupun kontrak API `GET /api/search?q=<kueri>&top_k=10`.
3. **Pertahankan** semua `id` elemen dan nama fungsi yang dipakai `script.js` untuk memanggil API dan merender hasil. Kalau perlu mengganti struktur HTML, sesuaikan `script.js` agar fungsinya tetap sama.
4. Jangan menebak nama field JSON. Baca dulu respons `/api/search` dan kode `script.js` yang sudah ada, lalu pakai nama field yang sebenarnya.
5. Tanpa framework dan tanpa build step. Tetap **HTML + CSS + JavaScript vanilla**, dilayani Flask.
6. Kerjakan bertahap (lihat bagian 12) dan jalankan `python app.py` untuk memeriksa tampilan di `http://127.0.0.1:5000` setelah tiap tahap.

---

## 1. Konteks produk

- **Apa:** mesin pencari edukasi dan tips finansial pemula berbahasa Indonesia.
- **Fitur inti:** membandingkan peringkat **TF-IDF (Vector Space Model + Cosine Similarity)** dan **Okapi BM25** secara berdampingan untuk kueri yang sama.
- **Data tampilan:** statistik korpus (320 dokumen, 5.036 term unik, rata-rata 219,87 token per dokumen, 4 sumber), token hasil preprocessing Sastrawi, jumlah irisan Top-K kedua algoritma (`overlap_count`), latensi tiap algoritma, daftar hasil, dan modal baca artikel penuh.
- **Pengguna:** mahasiswa, dosen penguji, dan pembaca umum yang ingin memahami perbedaan dua algoritma peringkat. Mereka perlu memindai hasil dengan cepat dan melihat angka yang bisa dipercaya.

---

## 2. Prinsip desain

1. **Pencarian adalah pusat.** Kolom pencarian adalah elemen paling dominan di halaman.
2. **Tenang, bukan dekoratif.** Latar netral, sedikit bayangan, tanpa gradien dan efek berlebihan. Warna dipakai untuk makna, bukan hiasan.
3. **Perbandingan adalah bintang.** Dua algoritma punya identitas warna tetap di seluruh UI. Satu-satunya elemen yang boleh mencolok adalah panel perbandingan dan penanda perbedaan hasilnya.
4. **Transparan.** Skor, token, irisan, dan latensi ditampilkan sebagai bagian dari antarmuka karena ini proyek akademik.
5. **Cepat dipindai.** Hierarki jelas: judul, sumber, skor, cuplikan. Teks panjang dibatasi di bawah 80 karakter per baris.

---

## 3. Design tokens

Simpan di `static/tokens.css` dan muat sebelum `style.css`. Semua warna, ukuran, dan spasi di komponen **harus** memakai variabel ini, tanpa nilai hex atau piksel langsung.

```css
:root {
  color-scheme: light;

  /* Permukaan */
  --bg: #F7F8FA;
  --surface: #FFFFFF;
  --surface-sunken: #F1F3F6;
  --border: #E4E7EC;
  --border-strong: #CBD1DB;

  /* Teks */
  --text: #101828;
  --text-muted: #5B6676;
  --text-on-primary: #FFFFFF;

  /* Aksi utama (hijau-teal, kesan finansial yang tenang) */
  --primary: #0E7C66;
  --primary-hover: #0B6553;
  --primary-soft: #E3F4EF;

  /* Identitas algoritma, tetap konsisten di seluruh UI */
  --algo-a: #4F46E5;          /* TF-IDF (VSM) */
  --algo-a-soft: #EEF0FF;
  --algo-b: #B45309;          /* Okapi BM25 */
  --algo-b-soft: #FEF3C7;

  /* Status */
  --success: #15803D;
  --warning: #B45309;
  --danger: #B42318;

  /* Penanda kata kunci */
  --highlight-bg: #FEF08A;
  --highlight-text: #422006;

  /* Fokus keyboard */
  --focus-ring: 0 0 0 3px rgba(14, 124, 102, 0.35);

  /* Bentuk (radius bertingkat, bukan satu nilai untuk semua) */
  --radius-chip: 999px;
  --radius-control: 10px;
  --radius-card: 14px;
  --radius-modal: 18px;

  /* Spasi, kelipatan 4px */
  --space-1: 4px;  --space-2: 8px;   --space-3: 12px;
  --space-4: 16px; --space-5: 24px;  --space-6: 32px;
  --space-7: 48px; --space-8: 72px;

  /* Tipografi */
  --font-ui: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Consolas, monospace;
  --fs-xs: 0.75rem;   /* 12 */
  --fs-sm: 0.875rem;  /* 14 */
  --fs-md: 1rem;      /* 16 */
  --fs-lg: 1.25rem;   /* 20 */
  --fs-xl: 1.75rem;   /* 28 */
  --fs-2xl: 2.5rem;   /* 40 */

  /* Lebar konten */
  --content-max: 1200px;
  --reading-max: 68ch;

  /* Gerak */
  --ease: cubic-bezier(0.2, 0, 0, 1);
  --dur-fast: 120ms;
  --dur-base: 200ms;
}

:root[data-theme="dark"] {
  color-scheme: dark;

  --bg: #0B0F14;
  --surface: #131A22;
  --surface-sunken: #0F151C;
  --border: #243040;
  --border-strong: #33445A;

  --text: #E6EAF0;
  --text-muted: #98A2B3;
  --text-on-primary: #04130F;

  --primary: #34D1AE;
  --primary-hover: #5BE0C2;
  --primary-soft: rgba(52, 209, 174, 0.14);

  --algo-a: #A5B4FC;
  --algo-a-soft: rgba(129, 140, 248, 0.16);
  --algo-b: #FBBF24;
  --algo-b-soft: rgba(251, 191, 36, 0.14);

  --success: #4ADE80;
  --warning: #FBBF24;
  --danger: #F97066;

  --highlight-bg: rgba(250, 204, 21, 0.28);
  --highlight-text: #FEF9C3;

  --focus-ring: 0 0 0 3px rgba(52, 209, 174, 0.45);
}

/* Tema awal mengikuti sistem bila pengguna belum memilih */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    /* salin seluruh nilai dari :root[data-theme="dark"] di sini */
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

**Aturan tema:** atribut `data-theme` dipasang di `<html>`. Urutan penentuan: pilihan tersimpan pengguna (`localStorage`, dibungkus `try/catch`), lalu `prefers-color-scheme`, lalu terang. Sediakan tombol ganti tema di header.

---

## 4. Tipografi

- **UI dan isi:** Inter (400, 500, 600). **Angka teknis:** JetBrains Mono (400, 500) untuk skor, latensi, token, jumlah dokumen, dan metrik evaluasi.
- Muat lewat Google Fonts dengan `display=swap` dan fallback sistem seperti pada token.
- Skala: 12, 14, 16, 20, 28, 40 px.
- Judul halaman 40 px berat 600, jarak huruf sedikit rapat (`letter-spacing: -0.02em`). Judul bagian 20 px berat 600. Teks isi 16 px dengan `line-height: 1.6`. Teks kecil (sumber, tanggal, label) 12–14 px warna `--text-muted`.
- Gunakan `font-variant-numeric: tabular-nums` pada semua angka agar kolom sejajar.
- Batasi lebar cuplikan dan isi artikel pada `--reading-max`.

---

## 5. Layout

Gaya **bento grid** untuk statistik dan **dua kolom setara** untuk perbandingan. Lebar maksimum `--content-max`, rata kiri, dengan jarak antar-blok `--space-5`.

```text
┌──────────────────────────────────────────────────────────────┐
│ Header: logo FinEduSearch                       [Tema]        │
├──────────────────────────────────────────────────────────────┤
│ Judul singkat + deskripsi satu kalimat                         │
│ [ Kolom pencarian besar ................................ Cari ]│
│ (chip) kueri contoh  (chip)  (chip)  (chip)                    │
├──────────────────────────────────────────────────────────────┤
│ Bento statistik                                                │
│ ┌────────────┬──────────┬──────────┬──────────┐              │
│ │ 320        │ 5.036    │ 219,87   │ 4 sumber │              │
│ │ dokumen    │ term     │ token/dok│ (mini bar)│              │
│ └────────────┴──────────┴──────────┴──────────┘              │
├──────────────────────────────────────────────────────────────┤
│ Panel kueri: token Sastrawi (chip mono) │ Irisan: 6 dari 10    │
├──────────────────────────────────────────────────────────────┤
│ ┌── TF-IDF (VSM) ──────────┐  ┌── Okapi BM25 ─────────────┐   │
│ │ 0,12 ms · 10 hasil        │  │ 0,09 ms · 10 hasil        │   │
│ │ [kartu hasil]             │  │ [kartu hasil]             │   │
│ │ [kartu hasil]             │  │ [kartu hasil]             │   │
│ └───────────────────────────┘  └───────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

Responsif:
- **≥ 1024 px:** dua kolom perbandingan, bento 4 kolom.
- **640–1023 px:** bento 2 kolom, perbandingan tetap dua kolom bila muat, jika tidak berubah menjadi tab.
- **< 640 px:** satu kolom. Perbandingan menjadi **dua tab** (TF-IDF, BM25) dengan tab aktif memakai warna algoritmanya. Bento menjadi 2 kolom.
- Elemen yang lebar (tabel metrik) bergulir horizontal di dalam wadahnya sendiri, bukan di body.

---

## 6. Komponen

Gunakan nama kelas berprefiks `fe-` (contoh `fe-card`) agar tidak bentrok dengan kode lama.

### 6.1 Header dan tombol tema
Tinggi 56 px, border bawah 1 px `--border`, latar `--bg`. Logo berupa teks "FinEduSearch" berat 600 dengan satu ikon sederhana (SVG inline). Tombol tema berbentuk ikon dengan `aria-label` dan `aria-pressed`.

### 6.2 Search bar
- Tinggi 56 px, radius `--radius-control`, latar `--surface`, border 1 px `--border-strong`. Ikon kaca pembesar di kiri, tombol **Cari** berwarna `--primary` di kanan.
- Fokus: border `--primary` dan `box-shadow: var(--focus-ring)`.
- Mendukung Enter, `type="search"`, dan `autocomplete="off"`. Tombol bersihkan (×) muncul saat ada teks.
- **Chip kueri contoh:** pill (`--radius-chip`), latar `--surface-sunken`, teks 14 px. Hover mengubah border menjadi `--primary`. Klik langsung menjalankan pencarian.

### 6.3 Kartu statistik (bento)
Latar `--surface`, border 1 px, radius `--radius-card`, padding `--space-5`. Angka 28 px mono berat 500, label 14 px `--text-muted`. Kartu sumber artikel berisi bar horizontal tipis sebanding jumlah dokumen per sumber (Antara 162, Detik 146, Kompas 12). Tidak ada bayangan.

### 6.4 Panel kueri (token dan irisan)
- **Token:** chip mono 13 px berlatar `--surface-sunken`, diberi label "Token setelah Sastrawi".
- **Irisan:** teks "6 dari 10 hasil sama di kedua algoritma" dengan bar dua warna kecil (bagian irisan memakai `--primary`). Angka diambil dari `overlap_count`.

### 6.5 Header kolom algoritma
Strip atas setebal 3 px berwarna algoritma (`--algo-a` atau `--algo-b`), nama algoritma 20 px, keterangan kecil ("Cosine Similarity" atau "k1 = 1,5 · b = 0,75"), dan **badge latensi** mono ("0,12 ms"). Latar kolom `--algo-a-soft` atau `--algo-b-soft` hanya pada header, bukan seluruh kolom.

### 6.6 Kartu hasil
Susunan dari atas ke bawah:
1. Baris meta: nomor peringkat (mono, abu-abu), badge sumber (pill kecil), tanggal.
2. Judul 16 px berat 600, maksimal 2 baris, dapat diklik membuka modal.
3. Cuplikan 14 px `--text-muted` maksimal 3 baris. Kata kunci dibungkus `<mark>` bergaya `--highlight-bg` dan `--highlight-text`, radius 3 px, tanpa miring atau tebal.
4. Baris bawah: **badge skor** mono ("skor 0,482") berwarna sesuai algoritma, dan tautan "Sumber asli" (eksternal, `rel="noopener noreferrer"`, `target="_blank"`).

Penanda perbedaan: bila dokumen **hanya muncul di satu algoritma**, tampilkan pill kecil "Hanya di TF-IDF" atau "Hanya di BM25" berwarna algoritmanya. Dokumen di kedua daftar tidak diberi penanda. Selisih peringkat boleh ditampilkan sebagai teks kecil ("naik 2" atau "turun 3") bila datanya tersedia.

Gaya: radius `--radius-card`, border 1 px `--border`, padding `--space-4`, jarak antar-kartu `--space-3`. Hover hanya mengubah warna border menjadi `--border-strong`, tanpa terangkat dan tanpa bayangan.

### 6.7 Modal artikel
Overlay `rgba(0,0,0,0.5)`, panel `--surface` dengan radius `--radius-modal`, lebar maksimum 760 px, isi bergulir di dalam panel. Header berisi judul, badge sumber, tanggal, tombol tutup, dan tautan sumber asli. Isi memakai `--reading-max` dan `line-height: 1.7`. Wajib: `role="dialog"`, `aria-modal="true"`, fokus berpindah ke dalam modal dan kembali ke pemicu saat ditutup, tutup dengan Esc dan klik overlay.

### 6.8 Tabel metrik evaluasi (opsional, jika ditambahkan)
Kolom: metrik, TF-IDF, BM25. Angka mono rata kanan, nilai terbaik per baris diberi teks tebal dan titik kecil berwarna algoritmanya. Header tabel lengket (`position: sticky`) di dalam wadah bergulir.

---

## 7. State

| State | Tampilan |
|---|---|
| Awal | Hanya hero, kueri contoh, dan statistik. Panel hasil disembunyikan. |
| Memuat | Skeleton: 3 kartu abu-abu per kolom dengan animasi denyut halus. Tombol Cari menampilkan indikator kecil dan dinonaktifkan. |
| Tanpa hasil | Teks "Tidak ada artikel yang cocok dengan kueri ini." disertai 3 chip kueri yang disarankan dari daftar kueri contoh. |
| Error | Blok bertepi `--danger` yang menjelaskan masalahnya ("Server tidak merespons. Periksa apakah `python app.py` masih berjalan.") dan tombol **Coba lagi**. |
| Kueri kosong | Pesan kecil di bawah kolom pencarian, fokus tetap di input. |

---

## 8. Gerak

- Maksimal satu gerakan otomatis: hasil muncul dengan fade 200 ms saat pencarian selesai. Tidak ada animasi masuk berulang di tiap bagian dan tidak ada efek hover yang menggeser elemen.
- Gerakan yang menjawab aksi pengguna (modal terbuka, tab berpindah) boleh, durasi `--dur-base`.
- Hormati `prefers-reduced-motion` seperti pada token.

---

## 9. Aksesibilitas

- Kontras teks minimal **4,5:1** dan komponen UI minimal 3:1 di kedua tema. Gunakan token yang sudah disediakan, karena warna algoritma sudah dipilih agar lolos.
- Warna **tidak boleh** menjadi satu-satunya pembeda dua algoritma. Selalu sertakan nama teks dan ikon (misalnya segitiga untuk TF-IDF, lingkaran untuk BM25) di header kolom dan badge skor.
- Semua elemen interaktif dapat diakses keyboard dengan fokus terlihat memakai `--focus-ring`.
- Gunakan HTML semantik: `header`, `main`, `section` dengan `aria-labelledby`, `article` untuk tiap hasil, `ul` untuk daftar, dan `button` untuk aksi.
- Area sentuh minimal 44 × 44 px di layar kecil.
- Bagian hasil diberi `aria-live="polite"` agar pembaca layar memberi tahu saat hasil baru muncul.
- Struktur halaman yang bersih dan semantik juga memudahkan mesin atau AI membaca isinya.

---

## 10. Teks antarmuka (bahasa Indonesia)

Sapaan netral, kalimat aktif, huruf kapital gaya kalimat, tanpa basa-basi.

- Judul: "Cari tips finansial, lihat dua algoritma bekerja."
- Deskripsi: "Bandingkan hasil TF-IDF dan BM25 untuk kueri yang sama."
- Placeholder: "Cari, misalnya: cara menabung untuk pemula"
- Tombol: "Cari", "Coba lagi", "Tutup", "Baca artikel", "Buka sumber asli"
- Label: "Token setelah Sastrawi", "Hasil yang sama di kedua algoritma"
- Satu aksi memakai satu nama yang sama di seluruh alur.

---

## 11. Hindari

- Gradien sebagai hiasan, bayangan tebal, efek kaca berlebihan, dan animasi masuk di setiap bagian.
- Semua kartu dengan radius dan bayangan yang sama. Pakai radius bertingkat seperti pada token.
- Label huruf kapital semua di atas setiap judul, string meta bersambung titik tengah ("A · B · C") di mana-mana, dan tanda panah "→" di setiap tombol atau tautan.
- Menekankan satu kata di judul dengan warna atau miring.
- Penomoran "01 / 02 / 03" untuk konten yang bukan urutan. Nomor peringkat hasil boleh karena memang urutan.
- Memakai warna algoritma untuk hal lain selain TF-IDF dan BM25.
- Nilai warna, ukuran, dan spasi yang ditulis langsung di komponen.

---

## 12. Rencana implementasi

Kerjakan berurutan, periksa tampilan di browser setelah tiap tahap, dan jangan lanjut bila ada fitur lama yang rusak.

1. **Fondasi:** buat `static/tokens.css`, muat font di `<head>`, tambahkan `data-theme` dan tombol ganti tema (JS kecil di `script.js`). Reset dasar dan gaya `body`.
2. **Header, hero, search bar, dan chip kueri** (6.1, 6.2).
3. **Bento statistik** (6.3). Ambil angka dari data yang sudah dikirim Flask ke template.
4. **Panel kueri** (6.4) dan **header kolom algoritma** (6.5).
5. **Kartu hasil** beserta penanda "Hanya di …" (6.6). Hitung perbedaan dengan membandingkan daftar ID dokumen kedua algoritma di `script.js`.
6. **Modal artikel** (6.7) dan semua **state** (bagian 7).
7. **Responsif** (tab di layar kecil) dan **aksesibilitas** (bagian 9).
8. **Pembersihan:** hapus CSS lama yang tidak terpakai dan pastikan tidak ada nilai warna atau ukuran langsung di komponen.

Struktur akhir yang diharapkan:

```text
static/
├── tokens.css        # variabel desain (bagian 3)
├── style.css         # reset, layout, komponen berprefiks fe-
└── script.js         # logika pencarian, tema, tab, modal
templates/
└── index.html
```

---

## 13. Daftar periksa penerimaan

- [ ] Pencarian, hasil dua kolom, highlight, dan modal artikel tetap berfungsi seperti sebelumnya.
- [ ] Tidak ada perubahan pada file backend dan kontrak API.
- [ ] Mode terang dan gelap tampil benar di semua komponen, dan pilihan tema tersimpan.
- [ ] Layout nyaman di lebar 360, 768, dan 1280 px tanpa scroll horizontal pada body.
- [ ] Seluruh elemen interaktif bisa dijangkau keyboard dengan fokus yang terlihat.
- [ ] Kontras teks lolos 4,5:1 di kedua tema.
- [ ] TF-IDF dan BM25 dapat dibedakan tanpa bergantung pada warna.
- [ ] Animasi dimatikan saat `prefers-reduced-motion` aktif.
- [ ] Tidak ada nilai warna, ukuran, atau spasi yang ditulis langsung di komponen.
