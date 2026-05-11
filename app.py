from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.future import select
from sqlalchemy import delete
from database import SessionLocal, engine, Base, database
from models import Place
from auth import authenticate_user, create_session, check_login
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import os
from deep_translator import GoogleTranslator

load_dotenv()

app = FastAPI(docs_url=None, redoc_url=None)  # Swagger UI'ı gizle

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Başlatma / Kapatma ────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await database.connect()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# ── Ana Sayfa ──────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    query = select(Place).order_by(Place.id)
    async with SessionLocal() as session:
        result = await session.execute(query)
        places = result.scalars().all()

    places_json = [
        {
            "id": p.id,
            "date": p.date,
            "name_modern": p.name_modern,
            "transport_type": p.transport_type,
            "latitude": p.latitude,
            "longitude": p.longitude,
            "is_in_ottoman": p.is_in_ottoman,
            "description_tr": p.description_tr,
            "description_en": p.description_en,
        }
        for p in places
    ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "places": places_json,
            "google_maps_key": os.getenv("GOOGLE_MAPS_API_KEY")
        }
    )


# ── Seyahat Albümü ─────────────────────────────────────────────────────────
@app.get("/album", response_class=HTMLResponse)
async def album_page(request: Request):
    base_path = Path("static/images")
    book1_path = base_path / "book1"
    book2_path = base_path / "book2"
    book1_path.mkdir(parents=True, exist_ok=True)
    book2_path.mkdir(parents=True, exist_ok=True)

    valid_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    def get_images(path):
        return [
            f"/static/images/{path.name}/{f.name}"
            for f in sorted(path.iterdir())
            if f.is_file() and f.suffix.lower() in valid_extensions
        ]

    return templates.TemplateResponse(
        request=request,
        name="album.html",
        context={
            "book1": get_images(book1_path),
            "book2": get_images(book2_path)
        }
    )


# ── Giriş Sistemi (URL gizlenmiş) ─────────────────────────────────────────
# URL: /login veya /admin yerine tahmin edilmesi zor /yonetim-giris kullanılıyor

@app.get("/yonetim-giris", response_class=HTMLResponse)
async def login_page(request: Request):
    from auth import verify_session
    token = request.cookies.get("session_token")
    
    # Token varsa ve geçerliyse yönlendir, yoksa hata verme
    if token and verify_session(token): 
        return RedirectResponse(url="/yonetim", status_code=302)
        
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.post("/yonetim-giris")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    if authenticate_user(username, password):
        response = RedirectResponse(url="/yonetim", status_code=303)
        token = create_session(username)
        response.set_cookie(
            key="session_token",
            value=token,
            httponly=True,       # JavaScript erişemez
            samesite="strict",   # CSRF koruması
            max_age=60 * 60 * 8  # 8 saat
        )
        return response
    # Hatalı giriş — aynı sayfaya dön, hata mesajı yok (bilgi sızdırmamak için)
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": True}
    )


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("session_token")
    return response


# ── Admin Panel ────────────────────────────────────────────────────────────
@app.get("/yonetim", response_class=HTMLResponse)
async def admin(request: Request, user=Depends(check_login)):
    if isinstance(user, RedirectResponse):
        return user
    query = select(Place).order_by(Place.id)
    async with SessionLocal() as session:
        result = await session.execute(query)
        places = result.scalars().all()
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={"places": places}
    )


@app.post("/yonetim/ekle")
async def add_place(
    request: Request,
    date: str = Form(...),
    name_modern: str = Form(...),
    transport_type: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    is_in_ottoman: bool = Form(False),
    description_tr: str = Form(""),
    description_en: str = Form(""),
    user=Depends(check_login)
):
    if isinstance(user, RedirectResponse):
        return user
    async with SessionLocal() as session:
        place = Place(
            date=date,
            name_modern=name_modern,
            transport_type=transport_type,
            latitude=latitude,
            longitude=longitude,
            is_in_ottoman=is_in_ottoman,
            description_tr=description_tr,
            description_en=description_en
        )
        session.add(place)
        await session.commit()
    return RedirectResponse(url="/yonetim?msg=added", status_code=303)


@app.get("/yonetim/sil/{place_id}")
async def delete_place(place_id: int, user=Depends(check_login)):
    if isinstance(user, RedirectResponse):
        return user
    async with SessionLocal() as session:
        query = select(Place).where(Place.id == place_id)
        result = await session.execute(query)
        place = result.scalar_one_or_none()
        if place:
            await session.delete(place)
            await session.commit()
    return RedirectResponse(url="/yonetim?msg=deleted", status_code=303)


@app.get("/yonetim/duzenle/{place_id}", response_class=HTMLResponse)
async def edit_page(request: Request, place_id: int, user=Depends(check_login)):
    if isinstance(user, RedirectResponse):
        return user
    async with SessionLocal() as session:
        query = select(Place).where(Place.id == place_id)
        result = await session.execute(query)
        place = result.scalar_one_or_none()
    return templates.TemplateResponse(request=request, name="edit.html", context={"place": place})


@app.post("/yonetim/duzenle/{place_id}")
async def edit_save(
    place_id: int,
    date: str = Form(...),
    name_modern: str = Form(...),
    transport_type: str = Form(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    is_in_ottoman: bool = Form(False),
    description_tr: str = Form(""),
    description_en: str = Form(""),
    user=Depends(check_login)
):
    if isinstance(user, RedirectResponse):
        return user
    async with SessionLocal() as session:
        query = select(Place).where(Place.id == place_id)
        result = await session.execute(query)
        place = result.scalar_one_or_none()
        if place:
            place.date = date
            place.name_modern = name_modern
            place.transport_type = transport_type
            place.latitude = latitude
            place.longitude = longitude
            place.is_in_ottoman = is_in_ottoman
            place.description_tr = description_tr
            place.description_en = description_en
            await session.commit()
    return RedirectResponse(url="/yonetim?msg=updated", status_code=303)


# ── Çeviri ────────────────────────────────────────────────────────────────
@app.post("/yonetim/cevir")
async def translate_text(request: Request, user=Depends(check_login)):
    if isinstance(user, RedirectResponse):
        return user
    try:
        data = await request.json()
        text = data.get("text")
        if not text:
            return {"translated_text": ""}
        translated = GoogleTranslator(source='tr', target='en').translate(text)
        return {"translated_text": translated}
    except Exception as e:
        return JSONResponse({"error": "Çeviri yapılamadı", "details": str(e)}, status_code=500)


# ── Excel Yükleme (oturum korumalı) ───────────────────────────────────────
def _parse_excel(df) -> list:
    """DataFrame'i Place listesine dönüştürür."""
    df.columns = [str(c).strip().lower().replace('ı', 'i').replace('i̇', 'i') for c in df.columns]
    translator = GoogleTranslator(source='tr', target='en')
    records = []

    lat_col     = next((c for c in df.columns if 'enlem' in c or 'lat' in c), None)
    lon_col     = next((c for c in df.columns if 'boylam' in c or 'lon' in c), None)
    osman_col   = next((c for c in df.columns if 'osman' in c), None)
    hist_col    = next((c for c in df.columns if 'tarih' in c), None)
    mod_col     = next((c for c in df.columns if 'lokasyon' in c or 'modern' in c), None)
    info_col    = next((c for c in df.columns if 'bilgi' in c or 'desc' in c), None)
    vehicle_col = next((c for c in df.columns if 'arac' in c or 'transport' in c or 'kullanilan' in c or 'vasita' in c), None)

    for index, row in df.iterrows():
        try:
            if not lat_col or not lon_col or pd.isna(row[lat_col]):
                continue

            transport_val = str(row[vehicle_col]).strip() if vehicle_col and not pd.isna(row.get(vehicle_col)) else ""
            is_ottoman_val = str(row[osman_col]).strip().lower() in ["evet", "true", "1", "yes"] if osman_col else False
            desc_tr = str(row.get(info_col, "")) if info_col else ""
            desc_tr = "" if desc_tr == "nan" else desc_tr.strip()
            desc_en = ""
            if desc_tr:
                try:
                    desc_en = translator.translate(desc_tr)
                except Exception:
                    pass

            records.append(Place(
                date=str(row.get(hist_col, "")) if hist_col else "",
                name_modern=str(row.get(mod_col, "")) if mod_col else "",
                transport_type=transport_val,
                latitude=float(row[lat_col]),
                longitude=float(row[lon_col]),
                is_in_ottoman=is_ottoman_val,
                description_tr=desc_tr,
                description_en=desc_en
            ))
        except Exception as e:
            print(f"Hata (Satır {index}): {e}")
    return records


@app.get("/yonetim/excel-yukle")
async def load_excel(user=Depends(check_login)):
    """1. Kitap Excel'ini yükler. Mevcut tüm verileri siler, yeniden yükler."""
    if isinstance(user, RedirectResponse):
        return user
    excel_path = Path("data/harita_kitap1.xlsx")
    if not excel_path.exists():
        return JSONResponse({"error": f"'{excel_path}' bulunamadı!"}, status_code=404)

    df = pd.read_excel(excel_path)
    records = _parse_excel(df)

    async with SessionLocal() as session:
        await session.execute(delete(Place))
        await session.commit()
        for r in records:
            session.add(r)
        await session.commit()

    return JSONResponse({"status": "success", "message": f"Eski veriler temizlendi. {len(records)} kayıt yüklendi."})


@app.get("/yonetim/excel-yukle-2")
async def load_excel_book2(user=Depends(check_login)):
    """2. Kitap Excel'ini yükler. Mevcut verileri korur, üstüne ekler."""
    if isinstance(user, RedirectResponse):
        return user
    excel_path = Path("data/harita_kitap2.xlsx")
    if not excel_path.exists():
        return JSONResponse({"error": "'data/harita_kitap2.xlsx' bulunamadı!"}, status_code=404)

    df = pd.read_excel(excel_path)
    records = _parse_excel(df)

    async with SessionLocal() as session:
        for r in records:
            session.add(r)
        await session.commit()

    return JSONResponse({"status": "success", "message": f"2. Kitap verisi yüklendi. {len(records)} kayıt eklendi."})


# ── Eski URL'leri yönlendir (admin.html linkleri için geriye dönük uyumluluk)
@app.get("/admin")
async def old_admin_redirect():
    return RedirectResponse(url="/yonetim", status_code=301)

@app.get("/load_excel")
async def old_load_excel_redirect():
    return RedirectResponse(url="/yonetim-giris", status_code=302)

@app.get("/load_excel_book2")
async def old_load_excel_book2_redirect():
    return RedirectResponse(url="/yonetim-giris", status_code=302)
