# Thomas Stevens Interactive Map

Thomas Stevens'ın 1884–1886 yılları arasında "penny-farthing" bisikletiyle gerçekleştirdiği dünya turunu, tarihi rota üzerinde interaktif bir harita ile görselleştiren web uygulaması. Proje, **TÜBİTAK 2209-A Üniversite Öğrencileri Araştırma Projeleri Destekleme Programı** kapsamında desteklenmiştir.

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Proje Yapısı](#proje-yapısı)
- [Yerel Kurulum](#yerel-kurulum)
- [Ortam Değişkenleri (.env)](#ortam-değişkenleri-env)
- [Veritabanı ve Excel Yükleme](#veritabanı-ve-excel-yükleme)
- [Admin Paneli](#admin-paneli)
- [Çoklu Dil Desteği](#çoklu-dil-desteği)
- [Canlıya Alma (Deployment)](#canlıya-alma-deployment)
- [Sunucu Gereksinimleri](#sunucu-gereksinimleri)
- [Sık Karşılaşılan Sorunlar](#sık-karşılaşılan-sorunlar)

---

## Genel Bakış

Uygulama, Stevens'ın rotası üzerindeki konak yerlerini (Place) bir SQLite veritabanında tutar ve bunları Google Maps üzerinde işaretler. Her konak için:

- Tarih (1884–1886 arası)
- Modern lokasyon adı
- Enlem / boylam
- Ulaşım tipi (bisiklet, deniz, vb.)
- Osmanlı topraklarında olup olmadığı bilgisi
- Türkçe ve İngilizce açıklama metni

bulunur. Site Türkçe / İngilizce dil seçeneğiyle çalışır ve ayrıca Stevens'ın kitaplarından (Book 1 / Book 2) taranmış sayfa görsellerinin bulunduğu bir "Albüm" sayfası içerir.

## Teknoloji Yığını

- **Backend:** Python 3 + [FastAPI](https://fastapi.tiangolo.com/)
- **Sunucu:** [Uvicorn](https://www.uvicorn.org/) (ASGI)
- **Veritabanı:** SQLite (async, `aiosqlite` + `SQLAlchemy` + `databases`)
- **Şablon motoru:** Jinja2
- **Frontend:** Bootstrap 5, Leaflet.js / Google Maps JS API, vanilla JS
- **Kimlik doğrulama:** Cookie tabanlı oturum (bcrypt ile hashlenmiş şifre)
- **Veri içe aktarma:** pandas + openpyxl (Excel) + deep-translator (Google Translate, TR→EN otomatik çeviri)

## Proje Yapısı

```
.
├── app.py                 # FastAPI uygulaması, tüm route'lar
├── auth.py                # Giriş / oturum / şifre doğrulama
├── database.py            # SQLAlchemy async engine ve session
├── models.py               # Place tablosu (SQLAlchemy modeli)
├── stevens.db             # SQLite veritabanı dosyası
├── requirements.txt       # Python bağımlılıkları
├── .env.example            # Örnek ortam değişkenleri
├── data/
│   ├── harita_kitap1.xlsx  # 1. kitap rota verisi
│   └── harita_kitap2.xlsx  # 2. kitap rota verisi
├── static/
│   └── images/
│       ├── book1/          # 1. kitap albüm görselleri
│       ├── book2/          # 2. kitap albüm görselleri
│       └── ...              # logo, arka plan vb.
└── templates/
    ├── index.html          # Ana harita sayfası
    ├── album.html           # Albüm sayfası
    ├── login.html           # Admin giriş sayfası
    ├── admin.html           # Admin paneli (CRUD + Excel yükleme)
    └── edit.html            # Konum düzenleme formu
```

## Yerel Kurulum

1. **Python 3.10+ kurulu olmalı.** Sanal ortam oluşturup etkinleştirin:

   ```bash
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```

2. **Bağımlılıkları kurun:**

   ```bash
   pip install -r requirements.txt
   ```

3. **`.env` dosyası oluşturun** (`.env.example`'ı kopyalayıp doldurun, detaylar aşağıda).

4. **Uygulamayı başlatın:**

   ```bash
   uvicorn app:app --reload
   ```

   Tarayıcıdan `http://127.0.0.1:8000` adresine gidin.

5. **İlk veri yüklemesi:** Admin paneline giriş yapıp (`/yonetim-giris`) "Excel Yükle" butonlarıyla `data/harita_kitap1.xlsx` ve `data/harita_kitap2.xlsx` dosyalarını içe aktarın (bkz. [Veritabanı ve Excel Yükleme](#veritabanı-ve-excel-yükleme)).

## Ortam Değişkenleri (.env)

`.env.example` dosyasını `.env` olarak kopyalayıp doldurun:

```env
# ── Veritabanı ──────────────────────────────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./stevens.db

# ── Gizli Anahtar (oturum imzalama için) ───────────────────────────────────
# Üretmek için: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=...

# ── Admin Kimlik Bilgileri ─────────────────────────────────────────────────
ADMIN_USERNAME=...

# Şifreyi hash'lemek için:
#   python3 -c "import bcrypt; print(bcrypt.hashpw(b'SIFRENIZ', bcrypt.gensalt()).decode())"
ADMIN_PASSWORD_HASH=...

# ── Google Maps API (opsiyonel, harita için gerekli) ────────────────────────
GOOGLE_MAPS_API_KEY=...
```

> **Not:** `.env.example` içinde `DATABASE_URL` satırı yer almıyor, ancak `database.py` bu değişkeni zorunlu olarak okuyor. `.env` dosyanıza yukarıdaki gibi eklemeniz gerekir, aksi halde uygulama başlatılırken hata verir.

`GOOGLE_MAPS_API_KEY` boş bırakılırsa harita yüklenmeyebilir; [Google Cloud Console](https://console.cloud.google.com/) üzerinden "Maps JavaScript API" için bir anahtar oluşturup ekleyin ve faturalandırmayı etkinleştirin.

## Veritabanı ve Excel Yükleme

Veriler `data/harita_kitap1.xlsx` ve `data/harita_kitap2.xlsx` Excel dosyalarından admin paneli üzerinden içe aktarılır. İçe aktarma sırasında `description_tr` (Türkçe açıklama) sütunu, Google Translate (deep-translator) ile otomatik olarak İngilizceye çevrilip `description_en` alanına yazılır — **bu adım internet bağlantısı gerektirir**.

- **`/yonetim/excel-yukle`** (1. Kitap): Veritabanındaki **tüm kayıtları siler** ve `harita_kitap1.xlsx`'i sıfırdan yükler.
- **`/yonetim/excel-yukle-2`** (2. Kitap): Mevcut kayıtları **silmeden** `harita_kitap2.xlsx` verilerini ekler.

Bu nedenle veritabanını sıfırdan oluşturmak isterseniz sırasıyla önce 1. kitabı, ardından 2. kitabı yüklemeniz gerekir (1. kitap yükleme tüm tabloyu temizlediği için).

Excel dosyalarındaki sütun adları küçük harfe çevrilip Türkçe karakterler normalize edilir; sütun eşlemesi `app.py` içindeki `_parse_excel` fonksiyonunda anahtar kelimelerle (enlem/lat, boylam/lon, tarih, lokasyon/modern, bilgi/desc, arac/transport, osman) yapılır.

Çok sayıda satır için çeviri yapılırken Google Translate hız sınırlamasına (rate limit) takılabilirsiniz; bu durumda işlemi birkaç dakika sonra tekrar deneyin.

## Admin Paneli

- Giriş adresi: **`/yonetim-giris`** (klasik `/login` veya `/admin` yerine tahmin edilmesi güç bir URL kullanılır).
- Giriş yaptıktan sonra **`/yonetim`** adresine yönlendirilirsiniz. Buradan:
  - Yeni konum ekleyebilir, düzenleyebilir, silebilirsiniz.
  - Açıklama girerken "İngilizceye Çevir ✨" butonuyla anlık çeviri alabilirsiniz.
  - Excel dosyalarını yeniden yükleyebilirsiniz.
- Oturumlar cookie tabanlıdır (`session_token`, `httponly`, `samesite=strict`, 8 saat geçerli).
- `/admin`, `/load_excel`, `/load_excel_book2` gibi eski URL'ler geriye dönük uyumluluk için ilgili yeni adreslere yönlendirilir.

## Çoklu Dil Desteği

Site Türkçe ve İngilizce olarak iki dilde çalışır:

- Sabit metinler `data-tr` / `data-en` attribute'ları ile HTML içinde tutulur ve JS ile dil değiştiğinde güncellenir.
- Konum açıklamaları veritabanındaki `description_tr` / `description_en` alanlarından gelir.
- Seçilen dil tarayıcının `localStorage`'ında (`stevens_lang`) saklanır, sayfa yenilense de korunur.

Yeni metin eklerken her zaman hem `data-tr` hem `data-en` değerlerini doldurmayı unutmayın; aksi halde dil değiştirildiğinde o öğe boş/Türkçe kalır.

## Canlıya Alma (Deployment)

### Genel Yaklaşım

Bu proje bir **ASGI** uygulamasıdır ve Uvicorn (veya Gunicorn + Uvicorn worker) ile çalıştırılır. Statik bir site değildir — Python sunucusu sürekli ayakta olmalıdır.

**Production komutu (örnek):**

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
```

veya Gunicorn ile:

```bash
gunicorn app:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000
```

> `--reload` flag'i sadece geliştirme ortamı içindir, production'da kullanılmamalıdır.

### Nginx Reverse Proxy (örnek)

```nginx
server {
    listen 80;
    server_name example.com;

    location /static/ {
        alias /var/www/thomas-map/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

SSL için Let's Encrypt (Certbot) önerilir.

### Süreç Yönetimi

Uygulamanın sunucu yeniden başladığında otomatik ayağa kalkması için bir process manager kullanın:

- **systemd** servis dosyası (Linux VPS için en sade çözüm)
- veya **PM2** / **supervisor**

Örnek systemd unit dosyası (`/etc/systemd/system/thomas-map.service`):

```ini
[Unit]
Description=Thomas Stevens Map
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/thomas-map
EnvironmentFile=/var/www/thomas-map/.env
ExecStart=/var/www/thomas-map/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

### Platform Seçenekleri

Proje küçük/orta ölçekli ve dosya tabanlı SQLite kullandığı için en pratik seçenekler:

- **VPS (DigitalOcean, Hetzner, AWS Lightsail, Linode vb.):** Tam kontrol, systemd + Nginx ile yukarıdaki kurulum doğrudan uygulanır. SQLite dosyası kalıcı disk üzerinde tutulur.
- **Railway / Render / Fly.io:** FastAPI/Uvicorn uygulamalarını doğrudan destekler. SQLite kullanıyorsanız **kalıcı disk (persistent volume)** eklemeniz gerekir, aksi halde her deploy'da `stevens.db` ve yüklenen görseller sıfırlanır.
- **PythonAnywhere:** Küçük projeler için uygundur, ASGI desteği sınırlı olabilir — WSGI adaptasyonu gerekebilir.

> **Önemli:** `static/images/book1` ve `static/images/book2` klasörleri, görsellerin boyutuna bağlı olarak oldukça büyük olabilir (bu projede ~150 MB+). Platformunuzun depolama ve dağıtım (deploy) boyutu limitlerini kontrol edin. Bazı serverless/konteyner tabanlı platformlarda büyük statik dosyalar için ayrı bir object storage (S3, Cloudflare R2 vb.) + CDN kullanmak daha uygundur.

## Sunucu Gereksinimleri

| Gereksinim | Açıklama |
|---|---|
| **İşletim sistemi** | Linux (Ubuntu/Debian önerilir), Windows da çalışır |
| **Python** | 3.10 veya üzeri |
| **RAM** | Minimum 512 MB (öneri: 1 GB+) — pandas/Excel işlemleri için |
| **Disk** | En az 1–2 GB boş alan (görseller + SQLite veritabanı için) |
| **İnternet erişimi** | Excel yükleme / otomatik çeviri sırasında Google Translate'e (`translate.google.com`) erişim gerekir |
| **Açık portlar** | 80/443 (HTTPS için reverse proxy), uygulama içeride 8000 portunda çalışır |
| **Kalıcı depolama** | `stevens.db` ve `static/images/` klasörü deploy'lar arasında korunmalı |

## Sık Karşılaşılan Sorunlar

- **Harita yüklenmiyor / boş görünüyor:** `GOOGLE_MAPS_API_KEY` eksik, geçersiz veya faturalandırma kapalı olabilir.
- **Çeviri çalışmıyor / "Çeviri yapılamadı" hatası:** Sunucunun `translate.google.com`'a internet erişimi yok veya Google rate-limit uyguluyor; birkaç dakika sonra tekrar deneyin.
- **`DATABASE_URL` hatası ile başlamıyor:** `.env` dosyasına `DATABASE_URL=sqlite+aiosqlite:///./stevens.db` satırını ekleyin.
- **Giriş yapılamıyor:** `ADMIN_PASSWORD_HASH` değerinin bcrypt ile doğru üretildiğinden emin olun (düz metin şifre çalışmaz).
- **2. kitap açıklamalarının İngilizcesi boş:** İlgili kayıtları yeniden yüklemek veya mevcut kayıtları güncellemek için admin panelindeki çeviri tamamlama özelliğini kullanın (varsa) ya da `/yonetim/excel-yukle` + `/yonetim/excel-yukle-2` sırasını yeniden çalıştırın.
