# LabMate — Türkçe Proje Özeti

[**English README**](../README.md) · [**Tüm sürümler**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) · [**Ana yol haritası**](../ROADMAP.md)

**LabMate**, Flipper Zero üzerinde **3,3 V dijital sinyalleri** ölçmek, üretmek, kaydetmek ve temel sorunları teşhis etmek için geliştirilen, Momentum Firmware odaklı **tek uygulamalı** bir elektronik teknisyeni araç setidir.

## Hangi sürümü indirmeliyim?

| Sürüm | Durum | Kime uygun? |
| --- | --- | --- |
| [**v1.8 Stable**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) | GitHub'daki **Latest** normal kararlı sürüm | Uyumlu Momentum Firmware/API kullananlar |
| [**v1.8 E11 — Custom Momentum Edition**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum) | Herkese açık, **özel firmware uyumluluk ön sürümü** | **Yalnızca eşleşen E11 yamalı Momentum firmware/native kaynakları bulunan cihazlar** |
| [Eski sürümler](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) | Arşiv korunuyor | Önceki Momentum API'leri ve test edilmiş eski kurulumlar |

**Önemli:** Stable olması her firmware üzerinde çalışacağı anlamına gelmez. Resmî Flipper firmware, Unleashed, Xtreme ve diğer özel yazılımlarda ayrıca uyumluluk/doğru SDK derlemesi gerekir. **E11 FAP normal/yamasız Momentum'a tek başına yüklenemez.** E11 tam firmware güncelleme paketi uzman incelemesi amaçlıdır; eski özel firmware'e birebir geri dönüşün çalıştığı kanıtlanmış değildir.

## Araçlar

- GPIO Monitor, Frequency Meter, Pulse Analyzer ve PWM Studio.
- Gerçek olay sayacı (Counter), Button Analyzer ve Threshold Alerts.
- microSD CSV Logger, Log History ve CRC korumalı üç Profile yuvası.
- UART Terminal (9600/38400/115200 baud).
- **Yalnızca eşleşen E11 özel firmware sürümü:** I²C Explorer ve isteğe bağlı DS18B20 1-Wire desteği. Gerçek I²C cihazından pozitif ACK ve harici DS18B20 dönüşümü henüz fiziksel PASS olarak bildirilmedi.

Menü sırası: **MEASURE → OUTPUT → RECORDS → COMM → INFO** (About en sonda).

## Donanım sınırları ve testler

**Doğrulanmış 3,3 V dijital sinyaller dışında** doğrudan bağlantı yapma. Bilinmeyen voltajları, 5 V logic, araç elektrik sistemlerini ve şebeke gerilimini Flipper GPIO'ya bağlama.

v1.8 E11 adayında sahip tarafından gerçekleştirilen 100 Hz / 1 kHz %50 dijital loopback, PWM STOP/RESTART, ESP32-S2 UART 115200 ve yeni CSV/Profile kaydetme–yeniden açma denemeleri **PASS olarak raporlandı**. Bunlar bağımsız osiloskop kalibrasyonu veya tüm native firmware servislerinin aynı anda çakışmasız çalıştığı anlamına gelmez.

Üniversitede bir öğretim görevlisi eşliğinde yapılacak **bağımsız osiloskop ölçümleri** ileri fiziksel doğrulama olarak planlanmaktadır; henüz yapılmış olarak işaretlenmez. Gerçek buton bounce, BME280 I²C ACK, DS18B20, yedek microSD hata denemeleri ve kimi native servis çakışmaları da ayrıca kayıtlıdır.

## v1.9 ve v2.0 hedefleri

| Sürüm | Asıl hedef | Şu an |
| --- | --- | --- |
| **v1.9** | Dijital **Logic Scope** (gerçek kenar zaman damgaları, tetikleme, taşma bildirimi) + **Signal Compare** (referans/tolerans karşılaştırması) | Plan/Draft; kod teslim edilmedi |
| **v2.0** | **LabMate Ultimate / Signal Doctor**; ölçüme dayalı sorun analizi, birleşik dashboard, ileri istatistikler ve tutarlı profesyonel arayüz | Planlanan nihai hedef |

İki ayrı ama birbirini tamamlayan belgeyi birlikte izliyoruz:

1. [**Resmî ana roadmap**](../ROADMAP.md): Hangi özelliği hangi sürümde yapacağımızı belirler.
2. [**Master Roadmap V2 kalite/uyumluluk eki**](MASTER_ROADMAP_V2_ADDENDUM.md): Kaynak sahipliği, firmware entegrasyonu, fiziksel test ve güvenli yayının koşullarını belirler.

[v1.9'a başlamadan önce açık iş denetimi](V1_9_PRESTART_TWO_ROADMAP_AUDIT_2026-10-17.md) bu iki yol haritasını aynı tabloda birleştirir. Önceki yayınların etiketleri, dosya SHA256 değerleri ve kullanıcı verileri korunur.

## Lisans

**SauronLAB / Sehmus**, [MIT lisansı](../LICENSE). Hata raporlarında Flipper firmware versiyonunu, LabMate FAP SHA256 değerini, hatanın nasıl oluştuğunu ve gerektiğinde kişisel veri içermeyen logları belirt.
