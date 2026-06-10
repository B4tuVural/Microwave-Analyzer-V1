# 📡 Mikrodalga Smith Diyagramı Analizörü

> **Microwave Smith Chart Analyzer** — An interactive, professional-grade impedance matching tool built with Python and Streamlit. Designed for microwave engineering students and engineers.

---

## 🖼️ Ekran Görüntüleri / Screenshots

| 2B Smith Diyagramı | 3B Smith Diyagramı |
|:---:|:---:|
| ![2D Smith](docs/screenshot_2d.png) | ![3D Smith](docs/screenshot_3d.png) |

| Devre Şeması | Karşılaştırma Tablosu |
|:---:|:---:|
| ![Circuit](docs/screenshot_circuit.png) | ![Table](docs/screenshot_table.png) |

---

## ✨ Özellikler / Features

### 📐 İnteraktif Smith Diyagramları
- **2B Smith Diyagramı** — Plotly tabanlı; kaydır, yakınlaştır, üzerine gelerek Z, Y, Γ ve VSWR değerlerini görüntüle
- **3B Smith Diyagramı** — Yarım küre projeksiyonu; yük yörüngesi yön belirteçleriyle gösterilir, her nokta etiketli
- En iyi 3 çözüm 2B ve 3B diyagramlarda otomatik işaretlenir
- Empedans (Z) / Admitans (Y) görünümü seçimi

### ⚡ Empedans Uygunlama
Toplam fiziksel uzunluğa göre **en iyiden en kötüye** sıralanmış 8 adet çözüm:

| # | Yöntem |
|---|--------|
| 1 | Seri kısa devre yan hat |
| 2 | Paralel kısa devre yan hat |
| 3 | Paralel açık devre yan hat |
| 4 | Seri açık devre yan hat |
| … | … |

### 🔧 Devre Şeması Üretimi
- Her çözüm için fiziksel olarak doğru devre çizimi (Plotly)
  - Paralel yan hat → iki ray arasına inen stub
  - Seri yan hat → üst iletken kesintisine eklenen yukarı stub
  - Çeyrek dalga transformatör → vurgulu λ/4 bölümü
- d ve ℓ boyutları ile uç tipi (açık/kısa devre) etiketleri

### 🧮 Adım Adım Çözüm
- Her çözüm için Türkçe matematiksel adımlar
- $x_{stub}$ / $b_{stub}$ LaTeX indisleriyle gösterim
- Normalize değerin yanı sıra gerçek reaktans değeri (Ω)

### 📊 Karşılaştırma Tablosu
- Tüm 8 çözüm tek tabloda, en iyiden en kötüye sıralı
- Tek düğmeyle tüm sütunlarda birim değiştirme: **λ → m → cm → mm → μm**

### 📏 Adaptif Birim Dönüşümü
| Büyüklük | Birimler |
|----------|---------|
| Uzunluk (d, ℓ) | λ → m → cm → mm → μm |
| Reaktans / Z | Ω → mΩ |

### 🧩 Devre Çözücü (Kademeli Ağ)
- Farklı **εr** ve **Z₀** değerlerinde iletim hatları, seri stub ve paralel stub ekleyerek kademeli devre kurma
- Yapı doğrudan yükten başlar; aradaki **d / l mesafeleri** iletim hattı elemanlarıyla, stub'lar düğümlere bağlanarak verilir (final sorusundaki kaskat yapı gibi)
- İletim hatlarına uzunluk, stub'lara **ℓ** boyu + uç tipi (açık/kısa)
- Uzunluklar **λ / m / cm / mm** cinsinden girilebilir
- Oluşan devrenin özellikleri (Z_in, Γ, VSWR, geri dönüş kaybı) ve ayrıntılı eleman tablosu
- Smith diyagramı üzerinde **sürekli yörünge** (her düğüm işaretli)
- Kademeli devre şeması (kalın/vurgulu iletim hatları, gerçek seri/paralel stub çizimleri)
- **Gömülü sekme**: giriş empedansı için stub eşleme çözümleri (Devre Şeması sayfasıyla aynı gösterim)

### ⚙️ Görünüm Ayarları (Ayrı Sekme)
- Sabit R/X eğrileri, VSWR çemberleri, geri dönüş kaybı halkaları
- Hat yörüngesi ve uygunlama noktaları gösterim kontrolü
- Admitans/Empedans diyagram modu

---

## 🏗️ Mimari / Architecture

```
smith_streamlit/
├── core/                   # Saf RF matematiği (dokunulmaz çekirdek)
│   ├── models.py           # Veri modelleri (LoadData, MatchingSolution …)
│   ├── rf_math.py          # Γ, VSWR, Z↔Y dönüşümleri
│   ├── smith_curves.py     # Sabit R/X eğrileri, yarım küre projeksiyonu
│   ├── transmission_line.py # Γ döndürme, Zin hesabı
│   ├── matching.py         # Stub, λ/4 uygunlama algoritmaları
│   └── units.py            # Frekans ve uzunluk birim dönüşümleri
│
├── services/
│   ├── analyzer.py         # SmithAnalyzer facade: tek çağrıyla tam analiz
│   └── cascade.py          # Kademeli ağ çözücü (saf motor; core'u besteler)
│
├── viz/                    # Saf Plotly figür üreticileri (Streamlit'ten bağımsız)
│   ├── theme.py            # Tek renk/font kaynağı (dark palette)
│   ├── smith_2d.py         # İnteraktif 2B Smith diyagramı
│   ├── smith_3d.py         # Yarım küre 3B Smith diyagramı
│   ├── circuit.py          # Devre şeması (primitif tabanlı tuval)
│   ├── cascade_smith.py    # Kademeli devre Smith yörüngesi (grid'i paylaşır)
│   └── cascade_circuit.py  # Kademeli devre şeması (canvas'ı paylaşır)
│
├── ui/                     # Streamlit arayüz katmanı
│   ├── inputs.py           # Kenar çubuğu giriş formu
│   ├── settings.py         # ⚙️ ViewSettings + ayar sayfası
│   ├── analysis_page.py    # 📊 Analiz sekmesi
│   ├── circuit_page.py     # 🔧 Devre şeması sekmesi (+ render_matching_solutions)
│   ├── cascade_page.py     # 🧩 Devre çözücü sekmesi (+ gömülü eşleme alt-sekmesi)
│   ├── unit_tools.py       # Birim döngüsü Streamlit düğmeleri
│   └── format.py           # Sayı biçimlendirme
│
├── unit_format.py          # Saf birim dönüşüm modülü (viz ve ui paylaşır)
├── app.py                  # Giriş noktası — 3 sekme orkestrasyon
└── .streamlit/
    └── config.toml         # Kalıcı dark tema
```

### Tasarım İlkeleri
- **Single Responsibility** — Her katman tek iş yapar (çekirdek hesap / figür üretimi / arayüz)
- **Open/Closed** — Yeni birim = `unit_format.py`'ye tek satır; yeni devre topolojisi = tek çizici fonksiyon
- **Dependency Inversion** — `viz/` katmanı Streamlit'i bilmez; yalnızca veri modellerine bağımlıdır

---

## 🖥️ Gereksinimler / Requirements

| Gereksinim | Sürüm |
|-----------|-------|
| Python | **3.11** (önerilen) |
| Streamlit | ≥ 1.40 |
| Plotly | ≥ 5.20 |
| NumPy | ≥ 1.24 |

---

## 🚀 Kurulum / Installation

### Windows (Önerilen)

```powershell
# 1. Projeyi klonla
git clone https://github.com/KULLANICI_ADI/smith-chart-analyzer.git
cd smith-chart-analyzer

# 2. Python 3.11 ile sanal ortam oluştur (Windows Python Launcher)
py -3.11 -m venv rf_venv

# 3. Sanal ortamı etkinleştir
rf_venv\Scripts\activate

# 4. Bağımlılıkları yükle
pip install -r requirements.txt

# 5. Uygulamayı başlat
streamlit run app.py
```

> **Not:** Tarayıcı otomatik açılmazsa `http://localhost:8501` adresine git.

---

### Linux / macOS

```bash
# 1. Projeyi klonla
git clone https://github.com/KULLANICI_ADI/smith-chart-analyzer.git
cd smith-chart-analyzer

# 2. Python 3.11 ile sanal ortam oluştur
python3.11 -m venv rf_venv

# 3. Sanal ortamı etkinleştir
source rf_venv/bin/activate

# 4. Bağımlılıkları yükle
pip install -r requirements.txt

# 5. Uygulamayı başlat
streamlit run app.py
```

---

### Sanal Ortamdan Çıkış

```bash
deactivate
```

---

## 📖 Kullanım / Usage

```
Uygulama 3 sekmeden oluşur:

📊 Analiz
  └── Sol kenar: yük empedansı, Z₀, frekans, hat uzunluğu, uygunlama yöntemi
  └── 2B / 3B Smith diyagramları (ayrı alt sekmeler)
  └── Temel analiz ve hat ilerleme tabloları (LaTeX indisler, birim gösterimi)

🔧 Devre Şeması
  └── Çözüm seçici (en iyiden en kötüye sıralı)
  └── Uzunluk (d, ℓ) ve reaktans birim değiştirme düğmeleri
  └── Plotly devre şeması + adım adım çözüm
  └── Tüm çözümlerin karşılaştırma tablosu (tek düğmeyle birim değiştir)

⚙️ Ayarlar
  └── Diyagram eğri/çember görünüm kontrolü
  └── Empedans / Admitans modu
```

---

## 🧪 Örnek Hesaplama / Example

```
Yük empedansı : Z_L = 100 + j100 Ω
Karakteristik  : Z₀  = 50 Ω
Frekans        : f   = 1.9 GHz
Faz hızı oranı: v/c = 0.667
Hat uzunluğu   : l   = 0.25 λ

→ 8 çözüm bulunur; en iyi: Seri kısa devre yan hat
  d = 0.1131 λ = 1.19 cm  |  ℓ = 0.1602 λ = 1.69 cm
  Gerekli stub reaktansı: X_stub = 79.06 Ω
```

---

## 🛠️ Teknolojiler / Tech Stack

| Teknoloji | Kullanım |
|-----------|---------|
| [Streamlit](https://streamlit.io) | Web arayüzü, sekme düzeni, widget'lar |
| [Plotly](https://plotly.com/python/) | İnteraktif 2B/3B Smith diyagramları, devre şeması |
| [NumPy](https://numpy.org) | RF hesaplamaları, vektör işlemleri |
| Python 3.11 | Tüm çekirdek mantık |

---

## 📜 Lisans / License

Bu proje [MIT Lisansı](LICENSE) kapsamında dağıtılmaktadır.

---

## 🎓 Notlar / Notes

- Uygulama arayüzü Türkçedir.
- Smith diyagramı hesaplamaları Pozar *Microwave Engineering* referans alınarak tasarlanmıştır.
- 3B diyagramda merkez (tepe) = uyum noktası (Γ=0), kenar (ekvator) = |Γ|=1.
- "En iyi çözüm" ölçütü: en kısa toplam fiziksel uzunluk (d + ℓ).

