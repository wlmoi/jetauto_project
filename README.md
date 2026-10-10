# JetAuto UART Research

Riset komunikasi UART JetAuto sebagai fondasi platform pemantauan dan kendali robot melalui web. Proyek ini diarahkan menjadi portofolio software, cloud, dan robotics engineering untuk mendukung lamaran pada posisi dengan kompetensi tersebut, termasuk posisi di ITB yang dimaksud dalam kebutuhan proyek.

Dokumen ini menjelaskan kondisi repository, masalah yang ingin diselesaikan, keputusan teknis, serta spesifikasi pengembangan. Fitur web dan cloud di bawah merupakan rancangan yang perlu diimplementasikan dan diuji. Kesesuaian proyek dengan kompetensi pekerjaan harus dinilai dari kontribusi pribadi dan bukti pengujian.

## Kondisi saat ini

Repository memuat kode driver JetAuto dan transkrip eksperimen serial. Pemeriksaan saat penyusunan README dilakukan pada kode dan berkas lokal. Robot, lingkungan ROS, serta layanan cloud belum diuji dalam pekerjaan dokumentasi ini.

| Bagian | Bukti dalam repository | Batas pembuktian |
| --- | --- | --- |
| Python dan UART | [SDK controller](jetauto_driver/jetauto_driver/ros_robot_controller/src/ros_robot_controller/ros_robot_controller_sdk.py) | Tersedia pembentukan paket, CRC8, parser penerimaan, dan akses serial |
| ROS1 | [Node controller](jetauto_driver/jetauto_driver/ros_robot_controller/scripts/ros_robot_controller_node.py) | Menggunakan `rospy`, publisher, subscriber, dan service |
| Sensor dan aktuator | SDK dan node controller | Tersedia akses IMU, baterai, motor, PWM servo, dan bus servo |
| Kinematika | [Mecanum](jetauto_driver/jetauto_driver/jetauto_sdk/src/jetauto_sdk/mecanum.py) | Tersedia konversi gerak chassis ke kecepatan roda |
| Odometri | [Publisher odometri](jetauto_driver/jetauto_driver/jetauto_controller/scripts/odom_publisher.py) | Posisi dihitung dari integrasi kecepatan perintah sehingga akurasi posisi fisik perlu diuji |
| Eksperimen serial | [Transkrip eksperimen](report.txt) | Memuat percobaan konfigurasi serial dan kegagalan `Argument types do not match` |
| Web, database, cloud, dan CI/CD | Belum tersedia dalam repository yang diperiksa | Masuk rencana pengembangan |

Kode driver yang tersedia menjadi bahan integrasi dan analisis. Kepemilikan kode tersebut tidak langsung membuktikan kontribusi pribadi. Perubahan sendiri perlu dicatat melalui commit, penjelasan desain, dan hasil pengujian. Identitas penulis pada kode asal perlu dipertahankan.

## Latar belakang masalah

Integrasi robot membutuhkan kesesuaian antara antarmuka listrik, konfigurasi serial, format paket, dan aplikasi kendali. Jika pembacaan serial gagal, pengembang perlu menentukan apakah penyebabnya berasal dari perangkat, konfigurasi, parser, atau program pengujian. Transkrip eksperimen dalam repository menunjukkan kegagalan pada program pengujian, sehingga hasil tersebut belum cukup untuk menyimpulkan baud rate atau kondisi controller.

Setelah komunikasi lokal dapat dipercaya, operator membutuhkan informasi kondisi robot yang mudah dibaca. Informasi tersebut mencakup koneksi, baterai, IMU, dan riwayat perintah. Karena koneksi jaringan dapat terputus, keputusan penghentian motor harus tetap dapat dilakukan pada robot tanpa menunggu layanan cloud.

Oleh karena itu, pengembangan proyek dimulai dari validasi UART, kemudian berlanjut ke gateway lokal, penyimpanan telemetri, dan dashboard web. Urutan ini membuat setiap lapisan memiliki bukti kerja sebelum dihubungkan ke lapisan berikutnya.

## Rumusan masalah

1. Bagaimana membuktikan konfigurasi dan format komunikasi controller melalui paket yang dapat diperiksa ulang?
2. Bagaimana mengubah data robot menjadi telemetri dengan satuan, timestamp, dan status kualitas yang jelas?
3. Bagaimana menerima perintah jarak jauh sambil menjaga batas gerak dan menangani koneksi terputus?
4. Bagaimana menyimpan riwayat sehingga masalah dapat ditelusuri dari dashboard sampai komunikasi perangkat?
5. Bagaimana menyiapkan deployment yang dapat diulang dan menunjukkan hasil pengujian secara transparan?

## Pola pikir perancangan

Setiap masalah ditangani melalui pengamatan, hipotesis, eksperimen, dan keputusan berdasarkan hasil. Sebagai contoh, kegagalan tipe data pada program capture perlu diperbaiki sebelum hasil capture digunakan untuk menilai protokol robot. Selanjutnya, paket mentah dibandingkan dengan implementasi SDK agar interpretasi data memiliki dasar yang dapat diperiksa.

Sistem dibagi menurut tanggung jawab. Driver menangani byte dan perangkat, gateway menangani validasi perintah serta telemetri, backend menangani identitas dan penyimpanan, sedangkan dashboard menangani interaksi operator. Dengan pembagian ini, gangguan pada database tidak perlu menghentikan pengamanan gerak lokal.

Prioritas awal adalah satu robot dengan satu operator aktif. Pengembangan beberapa robot dilakukan setelah identitas perangkat, penanganan duplikasi pesan, dan hak kendali sudah diuji. Setiap keputusan dicatat bersama alasan, pilihan lain yang dipertimbangkan, dan konsekuensinya.

## Produk yang direncanakan

**JetAuto Monitoring and Control Platform** menyediakan dashboard kondisi robot, riwayat telemetri, kendali terbatas, dan catatan aktivitas operator.

Arsitektur berikut merupakan target pengembangan.

```text
Controller JetAuto
    |
    | UART
    v
Driver Python dan ROS1
    |
    v
Gateway lokal dengan validasi dan watchdog
    |
    | MQTT melalui TLS
    v
Broker dan backend pada server lokal atau AWS
    |
    +--> PostgreSQL untuk telemetri dan audit
    |
    +--> HTTPS API dan WebSocket
              |
              v
       Dashboard Next.js dan TypeScript
```

Python digunakan untuk gateway karena dekat dengan SDK yang tersedia. Next.js dan TypeScript digunakan untuk dashboard serta kontrak data aplikasi. PostgreSQL dipilih untuk menyimpan identitas robot, telemetri, dan audit perintah. MQTT menghubungkan gateway dengan backend, HTTPS digunakan untuk login dan pembacaan riwayat, sedangkan WebSocket digunakan untuk pembaruan dashboard.

Deployment awal menggunakan server lokal agar integrasi perangkat dapat diamati. Setelah fungsi dan pengujian stabil, layanan backend dapat dipindahkan ke AWS. Pilihan ini membatasi jumlah platform yang perlu dipelajari pada tahap awal. Dukungan GCP atau Azure dapat ditambahkan jika kebutuhan deployment mengharuskannya.

## Spesifikasi fungsional

Seluruh spesifikasi berikut merupakan target awal. Angka dapat disesuaikan berdasarkan kemampuan perangkat dan hasil pengukuran yang dicatat.

| ID | Kebutuhan | Kriteria penerimaan |
| --- | --- | --- |
| F01 | Gateway membaca telemetri robot | Setiap sampel memiliki identitas robot, timestamp, nomor urut, nilai, satuan, dan status validitas |
| F02 | Dashboard menampilkan kondisi terkini | Menampilkan koneksi, baterai, IMU, dan usia data tanpa mengganti data hilang menjadi nol |
| F03 | Operator memberikan perintah gerak | Perintah memuat ID unik, batas waktu berlaku, identitas operator, dan nilai kecepatan yang tervalidasi |
| F04 | Robot berhenti saat perintah kedaluwarsa | Watchdog lokal mengirim perintah berhenti setelah 500 ms tanpa pembaruan perintah yang sah |
| F05 | Hak akses dibedakan | Viewer dapat melihat data, sedangkan operator yang memiliki sesi kendali dapat mengirim perintah |
| F06 | Telemetri dan perintah dapat ditelusuri | Riwayat dapat dicari menurut robot, waktu, dan ID perintah |
| F07 | Gateway menangani koneksi terputus | Gangguan jaringan dicatat, gerak dihentikan, dan perintah lama tidak dijalankan ketika tersambung kembali |
| F08 | Sistem dapat diuji tanpa robot | Simulator menyediakan telemetri dan skenario kegagalan dengan format yang sama dengan gateway |

Status perintah dibedakan menjadi diterima backend, diteruskan gateway, dikirim melalui UART, kedaluwarsa, dan ditolak. Status terkirim melalui UART tidak boleh ditampilkan sebagai bukti bahwa robot sudah bergerak. Konfirmasi pelaksanaan memerlukan umpan balik perangkat yang benar-benar mendukungnya.

## Spesifikasi kualitas dan keamanan

| Aspek | Target awal | Cara pembuktian |
| --- | --- | --- |
| Pembaruan dashboard | Telemetri 10 Hz dengan usia data persentil ke-95 di bawah 500 ms pada LAN pengujian | Catat jumlah sampel, durasi pengujian, dan selisih waktu dengan clock yang tersinkron |
| Penghentian lokal | Perintah nol dikirim paling lambat 100 ms setelah watchdog 500 ms berakhir | Rekam waktu perintah terakhir, pemicu watchdog, dan penulisan serial |
| Validasi paket | Paket CRC salah ditolak dan parser pulih ketika paket valid berikutnya datang | Replay paket valid, rusak, terpotong, dan byte tambahan |
| Integritas perintah | Perintah kedaluwarsa dan ID duplikat ditolak | Uji pengiriman ulang, reconnect, dan duplikasi MQTT |
| Otorisasi | Viewer dan perangkat tanpa kredensial tidak dapat mengendalikan robot | Uji akses API serta ACL topic MQTT |
| Deployment | Konfigurasi versi yang sama dapat dijalankan ulang | Jalankan prosedur deployment pada lingkungan bersih dan catat hasilnya |

Target penghentian di atas mengukur pengiriman perintah nol. Jarak dan waktu berhenti fisik harus diukur terpisah karena dipengaruhi beban, kecepatan, permukaan, serta respons controller.

TLS, pembatasan akses jaringan, validasi payload, pembatasan laju perintah, dan audit menjadi bagian dari desain. Kredensial perangkat dipisahkan dari akun operator dan disimpan di luar repository. Akses ROS dan UART tetap berada pada jaringan lokal robot. CRC8 digunakan untuk mendeteksi kerusakan paket, sedangkan autentikasi dan TLS menangani identitas serta perlindungan komunikasi jaringan.

## Detail UART yang perlu dibuktikan

SDK membuka perangkat default `/dev/rrc` dengan baud rate `1000000`. Nilai ini berasal dari kode dan perlu dikonfirmasi pada perangkat yang digunakan.

Implementasi `buf_write` menyusun paket kirim sebagai berikut.

```text
0xAA | 0x55 | function | payload_length | payload | CRC8
```

CRC8 dihitung dari field function, panjang payload, dan payload. Terdapat komentar awal pada SDK yang menyebut urutan berbeda, sehingga dokumentasi protokol harus membandingkan fungsi pengiriman, parser penerimaan, dan capture perangkat.

Untuk perintah motor, payload diawali subperintah `0x01` dan jumlah motor. Setiap motor dikodekan dengan indeks satu byte dan nilai float little-endian melalui format `<Bf`. SDK mengubah ID motor dari penomoran satu menjadi indeks mulai nol. Akses IMU mendekode enam float melalui format `<6f`, tetapi satuan dan arah sumbu perlu dikonfirmasi melalui node ROS serta pengujian orientasi perangkat.

Eksperimen awal dilakukan dengan capture pasif. Setelah format paket dipastikan, uji aktuator dilakukan pada area terkendali dengan kecepatan rendah dan akses penghentian fisik. Watchdog software harus diuji bersama kondisi gateway mati karena software yang berhenti tidak dapat terus mengirim perintah nol. Jika firmware controller mendukung timeout motor, perilakunya perlu diverifikasi. Jika tidak, mekanisme penghentian independen perlu dirancang.

## Model data yang direncanakan

| Entitas | Field utama | Tujuan |
| --- | --- | --- |
| `robots` | `id`, `name`, `firmware_version`, `last_seen_at` | Identitas perangkat |
| `telemetry_samples` | `robot_id`, `sequence`, `captured_at`, `received_at`, `payload`, `quality` | Riwayat pengukuran dan kualitas data |
| `commands` | `id`, `robot_id`, `operator_id`, `issued_at`, `expires_at`, `payload`, `status` | Penelusuran perintah |
| `audit_events` | `id`, `actor_id`, `robot_id`, `event_type`, `created_at`, `details` | Catatan perubahan dan akses |

Timestamp capture dan timestamp penerimaan dipisahkan agar keterlambatan jaringan dapat dianalisis. Unit setiap nilai disertakan dalam kontrak data. Indeks database disiapkan pada pasangan identitas robot dan waktu. Retensi awal telemetri ditetapkan tujuh hari untuk demo, kemudian kebutuhan penyimpanan dievaluasi dari volume data aktual.

## Dasar matematika dan kelistrikan

Konversi kecepatan tangensial roda ke putaran per detik mengikuti rumus yang digunakan dalam modul mecanum.

```text
rps = v / (pi * d)
```

`v` adalah kecepatan tangensial dalam meter per detik dan `d` adalah diameter roda dalam meter. Diameter roda harus mengikuti robot yang diuji karena perubahan diameter memengaruhi hasil konversi.

Estimasi posisi planar menggunakan kecepatan pada kerangka robot dan orientasi yaw.

```text
x_next = x + (vx * cos(yaw) - vy * sin(yaw)) * dt
y_next = y + (vx * sin(yaw) + vy * cos(yaw)) * dt
yaw_next = yaw + wz * dt
```

`dt` dinyatakan dalam detik dan `wz` dalam radian per detik. Integrasi kecepatan perintah dapat menyimpang saat roda selip atau motor tidak mencapai kecepatan target. Oleh karena itu, evaluasi odometri dilakukan dengan membandingkan estimasi terhadap pengukuran posisi nyata. Fusi sensor menjadi tahap lanjutan setelah karakteristik data diketahui.

Untuk kelistrikan, hubungan dasar yang digunakan adalah `V = I * R` dan `P = V * I`. Pemeriksaan perangkat mencakup tegangan logika UART, kecocokan TX dan RX, ground bersama untuk antarmuka yang memerlukannya, polaritas, serta kemampuan suplai arus motor. Nilai tegangan dan batas arus harus berasal dari spesifikasi board atau pengukuran yang benar. Data baterai dari SDK perlu dikonfirmasi satuannya sebelum dipakai untuk alarm.

## Hubungan dengan kompetensi posisi

| Kompetensi | Pekerjaan yang dapat dilakukan | Bukti yang perlu disiapkan |
| --- | --- | --- |
| TypeScript dan Python | Dashboard, kontrak API, gateway, serta alat analisis UART | Kode kontribusi sendiri, validasi data, dan demo integrasi |
| C atau C++ | Modul ROS2 C++ untuk validasi perintah atau parser yang kompatibel dengan capture | Source, build, dan pengujian paket. Firmware STM32 menjadi opsi jika source dan akses board tersedia |
| MySQL, MariaDB, atau PostgreSQL | Implementasi PostgreSQL untuk telemetri dan audit | Migrasi schema, query riwayat, dan analisis indeks |
| React atau Next.js | Dashboard robot dengan status koneksi dan riwayat | Demo UI, penanganan data kedaluwarsa, dan kontrol akses |
| DevOps dan version control | CI untuk lint, pengujian parser, build web, dan deployment container | Riwayat commit, hasil pipeline, serta prosedur rollback |
| Cloud dan on-premise | Jalankan sistem pada server lokal, kemudian deploy backend ke AWS | Diagram jaringan, konfigurasi deployment, log, dan pengukuran biaya aktual |
| MQTT, WebSocket, HTTP, dan TCP/IP | Implementasi alur telemetri serta perintah dan diagnosis koneksi | Kontrak pesan, ACL broker, pengujian reconnect, dan trace jaringan |
| RTSP dan WebRTC | Tambahkan pemantauan kamera setelah MVP stabil | Demo video, pengukuran latensi, dan penjelasan alur streaming |
| Embedded dan komunikasi | Analisis UART, framing, CRC8, timeout, dan integrasi controller | Capture paket beranotasi dan pengujian parser |
| Sensor mikrokontroler | Validasi IMU dan tegangan baterai | Tabel satuan, arah sumbu, noise, serta perbandingan pengukuran |
| Konsep kelistrikan | Dokumentasikan antarmuka dan kebutuhan suplai | Diagram koneksi serta catatan pengukuran |
| Lingkungan Linux | Konfigurasi serial, permission, service gateway, dan diagnosis log | Panduan setup yang berhasil dijalankan ulang |
| ROS1 atau ROS2 | Analisis node yang ada dan integrasi gateway, kemudian port satu node ke ROS2 jika dibutuhkan | Diagram topic, rekaman data, dan demo publisher serta subscriber |
| Internet security | Autentikasi, otorisasi, TLS, validasi input, dan pengelolaan secret | Skenario akses ditolak, konfigurasi, dan hasil pengujian |
| Bekerja di bawah tekanan | Latihan gangguan dengan batas waktu dan prioritas pemulihan | Timeline insiden, alasan keputusan, waktu pemulihan, dan evaluasi setelah latihan |

Satu proyek dapat memberikan bukti lintas kompetensi, tetapi tingkat penguasaan harus mengikuti pekerjaan yang sudah selesai dan dapat dijelaskan. PostgreSQL cukup menjadi database utama untuk MVP. RTSP, WebRTC, ROS2, dan firmware C++ dapat dikerjakan bertahap sesuai kebutuhan. Kemampuan bekerja di bawah tekanan diperlihatkan melalui keputusan saat gangguan dan catatan pemulihan.

## Tahapan implementasi

1. **Validasi riset UART**. Perbaiki program capture, simpan paket mentah, tulis spesifikasi berdasarkan SDK dan perangkat, lalu uji CRC serta pemulihan parser. Tahap selesai ketika konfigurasi serial dan beberapa jenis paket dapat dibuktikan melalui capture.
2. **Gateway lokal dan simulator**. Buat format telemetri, validasi perintah, watchdog, serta simulasi kehilangan koneksi. Tahap selesai ketika alur pemantauan dan penghentian dapat diuji tanpa cloud.
3. **Dashboard dan database**. Bangun Next.js, API, PostgreSQL, login, serta riwayat perintah. Tahap selesai ketika viewer dan operator memiliki akses yang sesuai dan data dapat ditelusuri.
4. **Integrasi jaringan dan deployment**. Hubungkan gateway melalui MQTT, aktifkan TLS dan ACL, lalu siapkan container serta CI/CD. Tahap selesai ketika deployment bersih dan skenario reconnect berhasil diuji.
5. **Pembuktian portofolio**. Rekam demo, ukur latensi, uji gangguan, dan tulis hasilnya. C++ atau ROS2 serta streaming kamera ditambahkan setelah MVP memiliki bukti yang memadai.

## Rencana pengujian

Pengujian parser menggunakan rekaman byte agar dapat diulang tanpa perangkat. Skenario mencakup CRC salah, payload terpotong, byte sampah, beberapa paket berurutan, dan data dengan panjang tidak sesuai. Pengujian gateway mencakup perintah duplikat, kedaluwarsa, di luar batas, serta perebutan sesi kendali.

Pengujian integrasi dimulai dari simulator, kemudian berpindah ke robot dengan pengamanan fisik. Gangguan yang disuntikkan meliputi serial terlepas, broker terputus, gateway berhenti, dan database tidak tersedia. Hasil mencatat kondisi awal, langkah, perilaku yang diharapkan, perilaku aktual, serta bukti log.

Format laporan pengukuran menggunakan tabel berikut. Kolom hasil diisi setelah pengujian dilakukan.

| Skenario | Lingkungan dan durasi | Target | Hasil terukur | Bukti |
| --- | --- | --- | --- | --- |
| Telemetri LAN | Belum diuji | Usia data p95 di bawah 500 ms | Belum tersedia | Log dan data timestamp |
| Watchdog perintah | Belum diuji | Perintah nol dikirim dalam 600 ms dari perintah terakhir | Belum tersedia | Trace gateway dan serial |
| Reconnect jaringan | Belum diuji | Perintah lama tidak dieksekusi | Belum tersedia | Audit dan rekaman demo |
| Akses viewer | Belum diuji | Semua upaya kendali ditolak | Belum tersedia | Hasil pengujian otorisasi |

## Prasyarat menjalankan kode yang tersedia

Kode memerlukan lingkungan Linux, ROS1 dengan catkin, dependensi Python yang sesuai, dan controller yang terhubung ke serial. Nama perangkat `/dev/rrc` perlu diperiksa pada mesin tujuan. Hak akses serial diberikan kepada akun service yang digunakan.

Launch utama pada `jetauto_controller` merujuk paket `jetauto_description`, `jetauto_peripherals`, dan `jetauto_slam` yang tidak tersedia dalam repository ini. Karena itu, lingkungan robot asal atau paket pendukung yang sesuai perlu disiapkan sebelum menjalankan launch penuh. Panduan instalasi dan perintah menjalankan sistem akan dilengkapi setelah versi dependensi serta hasil build dikonfirmasi.

## Kontribusi dan materi penjelasan

Setiap perubahan pribadi perlu mencantumkan masalah, perubahan kode, alasan desain, dan hasil validasi. Pisahkan hasil analisis driver asal dari implementasi yang dibuat sendiri agar ruang kontribusi mudah dipahami.

Penjelasan proyek dalam wawancara dapat mengikuti urutan berikut.

1. Jelaskan masalah komunikasi dan kebutuhan operator dengan contoh kegagalan yang diamati.
2. Tunjukkan bagaimana penyebab dipisahkan melalui eksperimen dan capture paket.
3. Jelaskan pembagian driver, gateway, backend, database, dan dashboard.
4. Hubungkan keputusan protokol dan penyimpanan dengan kebutuhan sistem.
5. Tunjukkan pengukuran, kegagalan yang ditemukan, dan perbaikan yang dilakukan.
6. Tutup dengan batas kemampuan sistem dan tahap pengembangan berikutnya.

Contoh narasi setelah MVP benar-benar selesai dan diuji dapat berbentuk seperti ini.

> Saya mengembangkan gateway dan dashboard pemantauan JetAuto dari fondasi driver UART yang tersedia. Saya memulai dengan memvalidasi paket dan memperbaiki alat capture, kemudian menghubungkan data robot ke backend melalui MQTT. Dashboard menampilkan kondisi terkini dan riwayat, sedangkan gateway menangani validasi serta kedaluwarsa perintah secara lokal. Saya menguji kehilangan koneksi dan mengukur keterlambatan data untuk mengevaluasi perilaku sistem.

Narasi tersebut perlu disesuaikan dengan fitur yang sudah dikerjakan. Angka performa ditambahkan hanya setelah ada pengukuran. Repository, README, demo, dan penjelasan wawancara harus menyampaikan status yang sama.
