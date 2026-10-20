# LabMate — Türkçe Proje Özeti

[**English README**](../README.md) · [**Tüm sürümler**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) · [**Ana yol haritası**](../ROADMAP.md)

**Son yayın:** [v1.9 Stable — Logic Scope & Signal Compare (yalnızca E11 uyumlu firmware)](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.9). Normal Momentum için [v1.8 Latest](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) korunuyor.

**LabMate**, Flipper Zero üzerinde **3,3 V dijital sinyalleri** ölçmek, üretmek, kaydetmek ve temel sorunları teşhis etmek için geliştirilen, Momentum Firmware odaklı **tek uygulamalı** bir elektronik teknisyeni araç setidir.

## Hangi sürümü indirmeliyim?

| Sürüm | Durum | Kime uygun? |
| --- | --- | --- |
| [**v1.9 Stable — E11 Özel Momentum**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.9) | **Yayınlandı, Stable; yalnızca eşleşen E11 firmware** | Gerçek PC1 Logic Scope, A/B karşılaştırma, referans/tolerans ve doğrulanmış özel Momentum E11 yerel API'leri bulunan Flipper Zero |
| [**v1.8 Stable**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8) | GitHub'daki **Latest** normal kararlı sürüm | Uyumlu Momentum Firmware/API kullananlar |
| [**v1.8 E11 — Custom Momentum Edition**](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.8-e11-custom-momentum) | Herkese açık, **özel firmware uyumluluk ön sürümü** | **Yalnızca eşleşen E11 yamalı Momentum firmware/native kaynakları bulunan cihazlar** |
| [Eski sürümler](https://github.com/sehmusadsoy-ui/flipper-labmate/releases) | Arşiv korunuyor | Önceki Momentum API'leri ve test edilmiş eski kurulumlar |

**Önemli:** **En yeni ürün sürümü v1.9 Stable'dır**, ancak yalnızca **E11 yamalı Momentum firmware ile uyumludur**. Normal Momentum kullanıcıları için GitHub **Latest** hâlâ **v1.8 Stable**'dır. `main` dalındaki `application.fam` hâlâ v1.8 kodunu gösterir; gerçek v1.9 kaynakları [v1.9 sürüm etiketindedir](https://github.com/sehmusadsoy-ui/flipper-labmate/tree/v1.9). Bunlar farklı uyumluluk profilleridir, sürümün tamamlanmadığı anlamına gelmez.

Stable olması her firmware üzerinde çalışacağı anlamına gelmez. Resmî Flipper firmware, Unleashed, Xtreme ve diğer özel yazılımlarda ayrıca uyumluluk/doğru SDK derlemesi gerekir. **E11 FAP normal/yamasız Momentum'a tek başına yüklenemez.** E11 tam firmware güncelleme paketi uzman incelemesi amaçlıdır; eski özel firmware'e birebir geri dönüşün çalıştığı kanıtlanmış değildir.

## Araçlar

- GPIO Monitor, Frequency Meter, Pulse Analyzer ve PWM Studio.
- Gerçek olay sayacı (Counter), Button Analyzer ve Threshold Alerts.
- microSD CSV Logger, Log History ve CRC korumalı üç Profile yuvası.
- UART Terminal (9600/38400/115200 baud).
- **v1.9 E11 Stable:** Logic Scope (PC1'de gerçek sınırlı HIGH/LOW dijital dalga), A/B sıralı kayıt, frekans/duty/zaman ayrıntıları, 100 Hz ve 1 kHz referans/tolerans karşılaştırması. 256 kenar tamponu, en fazla 5 saniyelik yakalama, saat/tetikleme/taşma güvenlik kontrolleri bulunur; analog osiloskop, eşzamanlı çok kanallı ölçüm veya yüksek hızlı kalibrasyon iddiası yoktur.
- **Yalnızca eşleşen E11 özel firmware sürümü:** I²C Explorer ve isteğe bağlı DS18B20 1-Wire desteği. Gerçek I²C cihazından pozitif ACK ve harici DS18B20 dönüşümü henüz fiziksel PASS olarak bildirilmedi.

Menü sırası: **MEASURE → OUTPUT → RECORDS → COMM → INFO** (About en sonda).

## Donanım sınırları ve testler

**Doğrulanmış 3,3 V dijital sinyaller dışında** doğrudan bağlantı yapma. Bilinmeyen voltajları, 5 V logic, araç elektrik sistemlerini ve şebeke gerilimini Flipper GPIO'ya bağlama.

**v1.9 E11 Stable fiziksel kabul:** Eşleşen firmware'li Flipper'da PA7→PC1 100 Hz ve 1 kHz %50 dijital kare dalga görüntüleri; A/B kayıt ve +900 Hz karşılaştırma; HIGH/LOW/PERIOD ayrıntıları; yanlış hedefte FAIL, doğru referansta PASS ve STOP/BACK kaynak bırakma denemeleri **PASS**. Yerel Windows SDK FAP derlemesi ve yayımlanan 101.468 baytlık FAP SHA-256 `d8bb04cf6de6ebaa466e7487e619d9f68af21dac49df2aa51e91dfae1f9f55c2` doğrulandı. [Yayımlanan v1.9 Stable](https://github.com/sehmusadsoy-ui/flipper-labmate/releases/tag/v1.9).

v1.8 E11 adayında sahip tarafından gerçekleştirilen 100 Hz / 1 kHz %50 dijital loopback, PWM STOP/RESTART, ESP32-S2 UART 115200 ve yeni CSV/Profile kaydetme–yeniden açma denemeleri **PASS olarak raporlandı**. Bunlar bağımsız osiloskop kalibrasyonu veya tüm native firmware servislerinin aynı anda çakışmasız çalıştığı anlamına gelmez.

Üniversitede bir öğretim görevlisi eşliğinde yapılacak **bağımsız osiloskop ölçümleri** ileri fiziksel doğrulama olarak planlanmaktadır; henüz yapılmış olarak işaretlenmez. Gerçek buton bounce, BME280 I²C ACK, DS18B20, yedek microSD hata denemeleri ve kimi native servis çakışmaları da ayrıca kayıtlıdır.

## v1.9 ve v2.0 hedefleri

| Sürüm | Asıl hedef | Şu an |
| --- | --- | --- |
| **v1.9** | Dijital **Logic Scope** (gerçek kenar zaman damgaları, tetikleme, taşma bildirimi) + **Signal Compare** (referans/tolerans karşılaştırması) | **E11'e özel Stable yayımlandı**; normal Momentum için bağımsız sürüm yok |

| **v2.0** | **LabMate Ultimate / Signal Doctor**; ölçüme dayalı sorun analizi, birleşik dashboard, ileri istatistikler ve tutarlı profesyonel arayüz | Planlanan nihai hedef |

İki ayrı ama birbirini tamamlayan belgeyi birlikte izliyoruz:

1. [**Resmî ana roadmap**](../ROADMAP.md): Hangi özelliği hangi sürümde yapacağımızı belirler.
2. [**Master Roadmap V2 kalite/uyumluluk eki**](MASTER_ROADMAP_V2_ADDENDUM.md): Kaynak sahipliği, firmware entegrasyonu, fiziksel test ve güvenli yayının koşullarını belirler.

[v1.9'a başlamadan önce açık iş denetimi](V1_9_PRESTART_TWO_ROADMAP_AUDIT_2026-10-17.md) bu iki yol haritasını aynı tabloda birleştirir. Önceki yayınların etiketleri, dosya SHA256 değerleri ve kullanıcı verileri korunur.

## Lisans

**SauronLAB / Sehmus**, [MIT lisansı](../LICENSE). Hata raporlarında Flipper firmware versiyonunu, LabMate FAP SHA256 değerini, hatanın nasıl oluştuğunu ve gerektiğinde kişisel veri içermeyen logları belirt.
