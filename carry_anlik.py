# -*- coding: utf-8 -*-
"""MADDE 728 — ANLIK POZİSYON GÖRÜNTÜSÜ (panel için, SALT OKUR).

Panel güvenlik gereği Binance'e bağlanmaz; pozisyonları günlük defterden (günde bir, 00:05 UTC) okuyordu, yani kâr / zarar
sütunu gün içinde hiç oynamıyordu. Bu betik açık pozisyonları ve işaret fiyatlarını okuyup `defter/anlik.json`'a yazar;
panel bu dosya tazeyse (PANEL: ANLIK_TAZE_SN) pozisyon tablosunu buradan gösterir, değilse günlük deftere döner.

HİÇBİR EMİR GÖNDERMEZ: yalnız get_open_positions + get_account_equity_usd. Günlük defter, rapor ve getiri serisi değişmez.
Sunucuda carry-anlik.timer ile 5 dakikada bir çalışır (deploy/carry-anlik.*). Elle:
    cd /opt/carry && sudo -u carry .venv/bin/python carry_anlik.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone

from carry_gunluk_defter import DEFTER_DOSYA, DEFTER_KLASOR, _pozisyonlar

ANLIK_DOSYA = os.path.join(DEFTER_KLASOR, "anlik.json")
BIRIKIM_DOSYA = os.path.join(DEFTER_KLASOR, "gelir_birikim.json")
GUN_DOSYA = os.path.join(DEFTER_KLASOR, "anlik_gun.json")
ORTUSME_MS = 10 * 60 * 1000   # geç düşen gelir kaydı kaçmasın: son 10 dk yeniden sorulur, tranId ile tekilleşir
GERCEK_DOSYA = os.path.join(DEFTER_KLASOR, "gercek_funding.json")
POZ_GECMIS_DOSYA = os.path.join(DEFTER_KLASOR, "anlik_poz.json")
POZ_GECMIS_GUN = 14
EMIR_DB = os.getenv("CARRY_EMIR_DB", os.path.join(DEFTER_KLASOR, "carry.db"))
GERCEK_ORTUSME_MS = 30 * 60 * 1000   # madde 747: gerçek borsa funding kaydını geç yayınlarsa kaçmasın
TOHUM_PENCERE_MS = 8 * 3600 * 1000   # tohum: gerçek funding anına en yakın demo funding kaydı bu kadar yakınsa pozisyon vardı sayılır
GUN_DEVIR_SN = 15 * 60        # önceki günün son noktası gün başına bu kadar yakınsa yeni günün açılış değeri olur


def poz_gecmis_ekle(dosya: str, simdi: float, poz: dict, sakla_gun: float = POZ_GECMIS_GUN) -> dict:
    """MADDE 745: panelin olaylar sayfası için pozisyon GEÇMİŞİ (coin başına [zaman, miktar, ortalama giriş]).
    Yalnız DEĞİŞİNCE satır eklenir (5 dk'da bir okunur; dilim turu / kâr al / stop sonrası ortalama buradan gösterilir).
    Kapanan coin [zaman, 0, 0] ile işaretlenir. sakla_gun'den eski satırlar atılır (her coinin son durumu korunur)."""
    try:
        with open(dosya, encoding="utf-8") as f:
            d = json.load(f).get("s") or {}
    except (OSError, ValueError, TypeError, AttributeError):
        d = {}
    t = int(simdi)
    for sem in set(d) | set(poz):
        m = float(poz[sem]["miktar"]) if sem in poz else 0.0
        g = float(poz[sem]["giris"]) if sem in poz else 0.0
        h = d.get(sem) or []
        if h and abs(h[-1][1] - m) <= 1e-12 * max(1.0, abs(m)) and abs(h[-1][2] - g) <= 1e-12 * max(1.0, g):
            continue
        if not h and m == 0:
            continue
        h.append([t, m, g])
        d[sem] = h
    sinir = t - sakla_gun * 86400
    for sem in list(d):
        h = d[sem]
        i = 0
        while i < len(h) - 1 and h[i + 1][0] < sinir:
            i += 1
        h = h[i:]
        if len(h) == 1 and h[0][1] == 0 and h[0][0] < sinir:
            del d[sem]
        else:
            d[sem] = h
    out = {"s": d}
    _atomik_yaz(dosya, out)
    return out


def gun_egri_ekle(dosya: str, simdi: float, deger: float) -> dict:
    """MADDE 742: panelin "bugün" eğrisi için gün içi kitap noktası. deger = özkaynak − başlangıçtan beri transfer
    (yatırma / çekme eğride sıçrama yapmasın). Gün = UTC günü (00:00 UTC = 03:00 TR); gün değişince dosya sıfırlanır.
    Önceki günün son noktası yeni günün başına GUN_DEVIR_SN'den yakınsa gün başı (açılış) değeri olarak taşınır."""
    bas = int(simdi) // 86400 * 86400
    gun = time.strftime("%Y-%m-%d", time.gmtime(bas))
    try:
        with open(dosya, encoding="utf-8") as f:
            d = json.load(f)
        nok = [[int(t), float(v)] for t, v in d.get("nok") or []]
    except (OSError, ValueError, TypeError, AttributeError):
        d, nok = {}, []
    if d.get("gun") != gun:
        nok = [[bas, nok[-1][1]]] if nok and bas - GUN_DEVIR_SN <= nok[-1][0] < bas else []
    nok.append([int(simdi), round(float(deger), 4)])
    d = {"gun": gun, "nok": nok[-400:]}
    _atomik_yaz(dosya, d)
    return d


def _ilk_zaman(defter_dosya: str) -> int | None:
    """Günlük defterin İLK satırının zamanı (= panelin 'başlangıç'ı)."""
    try:
        with open(defter_dosya, encoding="utf-8") as f:
            for l in f:
                if l.strip():
                    return int(json.loads(l)["zaman"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return None


def _atomik_yaz(dosya: str, veri: dict) -> None:
    os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
    gecici = dosya + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:   # yarım dosya okunmasın: önce geçici, sonra tek adımda değiştir
        json.dump(veri, f, ensure_ascii=False)
    os.replace(gecici, dosya)


def gelir_birikim(client, bas_s: int, simdi: float, dosya: str = BIRIKIM_DOSYA) -> dict:
    """MADDE 733: başlangıçtan beri gelir türü toplamları (funding, komisyon, gerçekleşen, transfer), ARTIMLI.
    Her çalışmada yalnız son kayıttan bu yana sorulur (10 dk örtüşme + tranId tekilleştirme). Borsa okunamazsa
    istisna yukarı çıkar ve birikim DEĞİŞMEZ (eksik sayılmaz)."""
    bas_ms = int(bas_s) * 1000
    try:
        with open(dosya, encoding="utf-8") as f:
            b = json.load(f)
        if b.get("bas_ms") != bas_ms:
            raise ValueError("başlangıç değişti")
    except (OSError, ValueError, AttributeError):
        b = {"bas_ms": bas_ms, "son_ms": bas_ms, "toplam": {}, "idler": {}, "coin": {}}
    bit_ms = int(simdi * 1000)
    idler = dict(b.get("idler") or {})   # kimlik -> kayıt zamanı (ms); yalnız örtüşme penceresindekiler saklanır
    toplam = dict(b.get("toplam", {}))
    coin = b.get("coin")
    if coin is None:   # madde 753: coin kırılımı sonradan eklendi — eski dosyada yok: başlangıçtan son_ms'e kadar bir kez kur
        coin = _coin_gecmis(client, bas_ms, int(b["son_ms"]))
    coin = {k: dict(v) for k, v in coin.items()}
    yeni_fund = []   # madde 749: bu çalışmada İLK KEZ görülen funding kayıtları (olaylar sayfası için)
    s = max(bas_ms, int(b["son_ms"]) - ORTUSME_MS)
    son = bit_ms
    for _ in range(50):
        r = client.client.futures_income_history(startTime=s, endTime=bit_ms, limit=1000)
        for g in r:
            kimlik = f"{g.get('tranId')}:{g.get('incomeType')}:{g.get('symbol')}"
            if kimlik in idler:
                continue
            idler[kimlik] = int(g["time"])
            t = g.get("incomeType") or "?"
            toplam[t] = toplam.get(t, 0.0) + float(g.get("income") or 0)
            if g.get("symbol"):   # madde 753: coin başına (panel "coin bazında kâr / zarar")
                c_ = coin.setdefault(g["symbol"], {}); c_[t] = c_.get(t, 0.0) + float(g.get("income") or 0)
            if t == "FUNDING_FEE" and g.get("symbol"):
                yeni_fund.append((int(g["time"]), g["symbol"], float(g.get("income") or 0)))
        if len(r) < 1000:
            break
        s = int(r[-1]["time"]) + 1
    else:
        son = s - 1   # 50 sayfa yetmedi: kalanı sonraki çalışmada
    idler = {k: t for k, t in idler.items() if t >= son - 2 * ORTUSME_MS}
    b = {"bas_ms": bas_ms, "son_ms": son, "toplam": {k: round(v, 6) for k, v in toplam.items()}, "idler": idler,
         "coin": {s_: {k: round(v, 6) for k, v in c_.items()} for s_, c_ in coin.items()}}
    _atomik_yaz(dosya, b)
    return {**b, "_yeni_funding": yeni_fund}


def _coin_gecmis(client, bas_ms: int, son_ms: int) -> dict:
    """MADDE 753: [bas_ms, son_ms] arasındaki gelir kayıtlarının coin × tür toplamı (tranId tekil). Okunamazsa istisna
    yukarı çıkar (birikim değişmez, sonraki çalışmada yeniden denenir)."""
    coin, gor, s = {}, set(), bas_ms
    for _ in range(100):
        if s > son_ms:
            break
        r = client.client.futures_income_history(startTime=s, endTime=son_ms, limit=1000)
        for g in r:
            kimlik = f"{g.get('tranId')}:{g.get('incomeType')}:{g.get('symbol')}"
            if kimlik in gor or not g.get("symbol"):
                continue
            gor.add(kimlik); t = g.get("incomeType") or "?"
            c_ = coin.setdefault(g["symbol"], {}); c_[t] = c_.get(t, 0.0) + float(g.get("income") or 0)
        if len(r) < 1000:
            break
        s = int(r[-1]["time"]) + 1
    return coin


STOP_DOSYA = os.path.join(DEFTER_KLASOR, "stop_durum.json")


def stop_hesapla(evren: list, longlar: list, g24, esik_coin: float, esik_piyasa: float) -> dict:
    """MADDE 753: koşullu 24 sa stop'un (carry_bot madde 622) şu anki durumu — panel için, SAF fonksiyon.
    g24(sembol) -> son KAPANMIŞ 4 sa mumunun 24 sa getirisi (carry_bot._kapanis_24s ile aynı ölçü) ya da None.
    Piyasa = evrenin medyanı (en az 10 coin; bot da öyle). Long başına coin getirisi ve eşiğe kalan mesafe."""
    ev = [v for v in (g24(s) for s in evren) if v is not None]
    ev.sort()
    med = None
    if len(ev) >= 10:
        n = len(ev); med = ev[n // 2] if n % 2 else (ev[n // 2 - 1] + ev[n // 2]) / 2
    cl = {}
    for s in longlar:
        v = g24(s)
        if v is not None:
            cl[s] = round(v, 4)
    return {"medyan": None if med is None else round(med, 4), "n": len(ev), "esik_coin": esik_coin, "esik_piyasa": esik_piyasa,
            "piyasa_sart": med is not None and esik_piyasa > 0 and med <= -esik_piyasa, "coin": cl}


def stop_durum(client, poz: dict, simdi: float, dosya: str = STOP_DOSYA, kitap: float | None = None) -> dict | None:
    """MADDE 753: stop_hesapla'yı SAATTE BİR çalıştırır (bot da piyasa medyanını saatte bir ölçer; değer yalnız 4 sa mum
    kapanınca değişir). Evren ve 24 sa ölçüsü botun kendi fonksiyonlarıyla (carry_bot.evren_sec / _kapanis_24s, gerçek
    Binance herkese açık verisi) — EMİR YOK, bot durumuna dokunmaz. Long seti değişince de yeniden ölçülür."""
    longlar = sorted(s for s, p in poz.items() if p.get("yon") == "L")
    saat = int(simdi // 3600)
    try:
        with open(dosya, encoding="utf-8") as f:
            eski = json.load(f)
        if eski.get("saat") == saat and eski.get("longlar") == longlar:
            return eski
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    import logging
    logging.getLogger("carry_bot").setLevel(logging.CRITICAL)   # botun log satırları bu süreçte yazılmasın
    import onerilen
    if onerilen.gerekli():   # bot açılışta "önerilen ayar"ı ortama yazıp kendini yeniden başlatır; aynı çözümleme burada
        onerilen.cozumle(lambda: kitap)
    import carry_bot as cb
    if cb.LONG_24S <= 0 or cb.LONG_24S_PIYASA <= 0:
        d = {"saat": saat, "zaman": int(simdi), "kapali": True, "coin": {}, "longlar": longlar}
    else:
        evren = cb.evren_sec(client)
        d = stop_hesapla(evren, longlar, lambda s_: cb._kapanis_24s(client, s_), cb.LONG_24S, cb.LONG_24S_PIYASA)
        d.update(saat=saat, zaman=int(simdi), longlar=longlar)
    _atomik_yaz(dosya, d)
    return d


def _veri_istemcisi(client):
    """Demoda gerçek Binance'in herkese açık istemcisi (exchange_client: veri / veri_gercek, madde 726); canlıda None
    (canlıda funding zaten gerçek orandan ödenir, ayrı hesap gereksiz)."""
    v = getattr(client, "veri", None)
    return v if v is not None and getattr(client, "veri_gercek", False) is True else None


def _tohum(client, v, bas_ms: int, bit_ms: int) -> float:
    """MADDE 744: başlangıçtan ilk çalışmaya kadarki gerçek-oran funding'i (geriye dönük, YAKLAŞIK). Demo funding kaydından
    o andaki imzalı pozisyon büyüklüğü çıkarılır (gelir = −büyüklük × demo oranı), gerçek borsanın funding anlarına
    TOHUM_PENCERE_MS içindeki en yakın kayıtla uygulanır. Borsa okunamazsa istisna yukarı çıkar (yanlış tohum yazılmaz)."""
    gel, s = [], bas_ms
    for _ in range(20):
        r = client.client.futures_income_history(incomeType="FUNDING_FEE", startTime=s, endTime=bit_ms, limit=1000)
        gel += r
        if len(r) < 1000:
            break
        s = int(r[-1]["time"]) + 1
    top = 0.0
    for sem in sorted({g["symbol"] for g in gel if g.get("symbol")}):
        demo = {int(x["fundingTime"]) // 60000: float(x["fundingRate"])
                for x in client.client.futures_funding_rate(symbol=sem, startTime=bas_ms - 3600000, endTime=bit_ms, limit=1000)}
        buyukluk = []
        for g in gel:
            if g.get("symbol") == sem:
                o = demo.get(int(g["time"]) // 60000)
                if o:
                    buyukluk.append((int(g["time"]), -float(g["income"]) / o))
        if not buyukluk:
            continue
        for x in v.futures_funding_rate(symbol=sem, startTime=bas_ms, endTime=bit_ms, limit=1000):
            t = int(x["fundingTime"])
            yakin = [b for b in buyukluk if abs(b[0] - t) <= TOHUM_PENCERE_MS]
            if yakin:
                top += -min(yakin, key=lambda b: abs(b[0] - t))[1] * float(x["fundingRate"])
    return top


def demo_funding(client, poz: dict, simdi: float) -> dict | None:
    """MADDE 748: DEMO hesabın sıradaki funding ödemesi (yalnız demo). Demo borsa funding'i kendi takvimi ve oranıyla öder
    (ör. HOT gerçek borsada saatte bir, demoda 8 sa'te bir); panelin sayacı gerçek borsaya baktığı için demo hesaba o saatte
    para yatmayabiliyordu. Tek çağrı (premiumIndex, tüm semboller). T = açık pozisyonların demo funding saatlerinin en
    yakını; tahmin = YALNIZ o saatte ödeyen pozisyonlar × demo oranı. Canlıda / pozisyon yoksa None."""
    if _veri_istemcisi(client) is None or not poz:
        return None
    satir = client.client.futures_mark_price()
    satir = satir if isinstance(satir, list) else [satir]
    pi = {x["symbol"]: x for x in satir if isinstance(x, dict) and x.get("symbol")}
    simdi_ms = int(simdi * 1000)
    zaman = {}
    for sem in poz:
        x = pi.get(sem) or {}
        t = int(x.get("nextFundingTime") or 0)
        if t > simdi_ms - 60_000:
            zaman[sem] = t
    if not zaman:
        return None
    T = min(zaman.values())
    tahmin = 0.0
    for sem, t in zaman.items():
        if abs(t - T) < 60_000:
            x = pi[sem]; p = poz[sem]
            tahmin += -float(p["miktar"]) * (float(x.get("markPrice") or 0) or float(p.get("isaret") or 0)) * float(x.get("lastFundingRate") or 0)
    return {"T": T // 1000, "tahmin": round(tahmin, 4), "n": sum(1 for t in zaman.values() if abs(t - T) < 60_000)}


FUNDING_OLAY_DOSYA = os.path.join(DEFTER_KLASOR, "funding_olay.json")
FUNDING_OLAY_GUN = 14


def _dk(ms: int) -> str:
    return str(int(ms) // 60000 * 60000)


def _gercek_gecmis(client, defter_dosya: str, db: str, bas_ms: int, bit_ms: int) -> list:
    """MADDE 749: geçmiş gerçek-oran funding olayları (yalnız ilk kurulumda). Başlangıç pozisyonları (defterin ilk satırı)
    + emir defterindeki dolumlar -> her an tutulan miktar; gerçek borsanın her funding anı × miktar × işaret × oran.
    Yeniden kurulan pozisyon borsadakiyle TUTMAZSA boş döner (yanlış geçmiş yazılmaz)."""
    import sqlite3
    with open(defter_dosya, encoding="utf-8") as f:
        ilk = json.loads(f.readline())
    bas_poz = {s_: float(p["miktar"]) for s_, p in (ilk.get("pozisyonlar") or {}).items() if "miktar" in p}
    t0 = int(ilk["zaman"]) * 1000
    olay = {}
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=2)
    try:
        for z, sem, yon, dolan, kap in c.execute("SELECT zaman, sembol, yon, dolan, kapanis FROM emir WHERE zaman>? AND dolan>0", (t0 / 1000,)):
            olay.setdefault(sem, []).append((int(float(kap or z) * 1000), float(dolan) * (1 if yon == "BUY" else -1)))
    finally:
        c.close()
    def miktar(sem, t):
        return bas_poz.get(sem, 0.0) + sum(d for ms, d in olay.get(sem, []) if ms <= t)
    borsa = {p["symbol"]: float(p["positionAmt"]) for p in client.get_open_positions() if abs(float(p.get("positionAmt") or 0)) > 0}
    semler = set(bas_poz) | set(olay) | set(borsa)
    if any(abs(miktar(s_, bit_ms) - borsa.get(s_, 0.0)) > 1e-6 * max(1.0, abs(borsa.get(s_, 0.0))) for s_ in semler):
        return []
    v = _veri_istemcisi(client); out = []
    for sem in sorted(semler):
        for x in v.futures_funding_rate(symbol=sem, startTime=max(bas_ms, t0), endTime=bit_ms, limit=1000):
            t = int(x["fundingTime"]); m = miktar(sem, t)
            if abs(m) > 1e-12:
                out.append((t, sem, -m * float(x["markPrice"]) * float(x["fundingRate"])))
    return out


def funding_olay_ekle(dosya: str, simdi: float, demo: list, gercek: list, sakla_gun: float = FUNDING_OLAY_GUN) -> dict:
    """MADDE 749: olaylar sayfası için funding ödemeleri. {"d": {dakika_ms: {sembol: demo hesaba yatan}},
    "g": {dakika_ms: {sembol: gerçek oranla olsaydı}}}; aynı (dakika, sembol) iki kez gelirse toplanmaz, üzerine yazılır
    (gelir_birikim / gercek_funding zaten tekilleştirir). sakla_gun'den eskiler atılır."""
    try:
        with open(dosya, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    for anahtar, liste in (("d", demo), ("g", gercek)):
        k = d.setdefault(anahtar, {})
        for t, sem, v in liste:
            k.setdefault(_dk(t), {})[sem] = round(k.get(_dk(t), {}).get(sem, 0.0) + float(v), 6) if anahtar == "d" else round(float(v), 6)
        sinir = (simdi - sakla_gun * 86400) * 1000
        d[anahtar] = {t: v for t, v in k.items() if int(t) >= sinir}
    _atomik_yaz(dosya, d)
    return d


def gercek_funding(client, bas_s: int, simdi: float, poz: dict, dosya: str = GERCEK_DOSYA) -> dict | None:
    """MADDE 744: "gerçek Binance oranlarıyla olsaydı" funding toplamı (yalnız demoda). Bot coin seçimini gerçek borsanın
    funding'ine göre yapar ama pozisyonlar demo borsada olduğu için funding'i demo borsa KENDİ oranıyla öder (çoğu zaman
    gerçekle ilgisiz, işareti bile ters). Her çalışmada, son çalışmadan bu yana gerçek borsada olan her funding anı için
    ŞU AN açık pozisyonlar × o anın işaret fiyatı × gerçek oran eklenir (5 dk'lık görüntü ~ funding anındaki pozisyon).
    İlk çalışmada geçmiş _tohum ile doldurulur. Borsa okunamazsa istisna yukarı çıkar, dosya DEĞİŞMEZ. Canlıda None."""
    v = _veri_istemcisi(client)
    if v is None:
        return None
    bas_ms, bit_ms = int(bas_s) * 1000, int(simdi * 1000)
    try:
        with open(dosya, encoding="utf-8") as f:
            b = json.load(f)
        if b.get("bas_ms") != bas_ms:
            raise ValueError("başlangıç değişti")
        top, son = float(b["toplam"]), int(b["son_ms"])
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        b = {"bas_ms": bas_ms, "son_ms": bit_ms, "toplam": round(_tohum(client, v, bas_ms, bit_ms), 6), "tohum_ms": bit_ms}
        _atomik_yaz(dosya, b)
        return b
    # MADDE 747: eskiden yalnız (son çalışma, şimdi] soruluyordu; gerçek borsa funding kaydını ödeme anından birkaç sn / dk
    # sonra yayınlarsa ödemeden hemen sonraki çalışma onu göremiyor, bir sonraki de ondan SONRASINI sorduğu için ödeme hiç
    # sayılmıyordu. Şimdi: coin başına en son sayılan funding anı saklanır; önceki çalışmada da açık olan coin için
    # GERCEK_ORTUSME_MS geriye bakılır, sayılmış anlar atlanır. Yeni açılan coin için geriye bakılmaz (açılmadan önceki
    # ödeme sayılmasın). Kapanan coinin kaydı silinir (yeniden açılırsa eski boşluk sayılmasın).
    sayilan = {k: int(t) for k, t in (b.get("sayilan") or {}).items()}
    onceki = set(b.get("poz") or [])
    yeni_say, yeni_olay = {}, []
    for sem, p in poz.items():
        if sem in sayilan:
            bas = max(sayilan[sem] + 1, son - GERCEK_ORTUSME_MS)
        elif sem in onceki:
            bas = son - GERCEK_ORTUSME_MS
        else:
            bas = son + 1
        en_son = sayilan.get(sem, 0)
        for x in v.futures_funding_rate(symbol=sem, startTime=bas, endTime=bit_ms, limit=50):
            t = int(x["fundingTime"])
            if t <= sayilan.get(sem, -1):
                continue
            fiyat = float(x.get("markPrice") or 0) or float(p.get("isaret") or 0)
            v_ = -float(p["miktar"]) * fiyat * float(x["fundingRate"])
            top += v_
            yeni_olay.append((t, sem, v_))
            en_son = max(en_son, t)
        if en_son:
            yeni_say[sem] = en_son
    gun = {k: float(v) for k, v in (b.get("gun") or {}).items()}   # madde 748: UTC gün başına gerçek funding (panel günlük grafiği)
    for t, _s, v_ in yeni_olay:
        g = datetime.fromtimestamp(t / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        gun[g] = round(gun.get(g, 0.0) + v_, 6)
    b.update(son_ms=bit_ms, toplam=round(top, 6), sayilan=yeni_say, poz=sorted(poz), gun=gun)
    _atomik_yaz(dosya, b)
    return {**b, "_yeni": yeni_olay}


def yaz(client=None, simdi: float | None = None, dosya: str = ANLIK_DOSYA,
        defter_dosya: str = DEFTER_DOSYA, birikim_dosya: str | None = None, emir_db: str | None = EMIR_DB) -> dict:
    if client is None:
        import config
        from exchange_client import ExchangeClient
        client = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    simdi = simdi or time.time()
    poz = _pozisyonlar(client)
    oz = float(client.get_account_equity_usd())
    olcek = float(os.getenv("CARRY_SERMAYE_OLCEK", "1.0") or 1.0)
    kayit = {
        "zaman": int(simdi),
        "ozkaynak": round(oz, 4),
        "kitap": round(oz * olcek, 4),
        "pozisyonlar": poz,
        "gerceklesmemis_top": round(sum(p["gerceklesmemis"] for p in poz.values()), 2),
    }
    try:   # madde 748: demo hesabın sıradaki funding'i (yalnız demo)
        df_ = demo_funding(client, poz, simdi)
        if df_ is not None:
            kayit["demo_funding"] = df_
    except Exception as ex:
        print(f"UYARI: demo funding saati okunamadı: {ex}", file=sys.stderr)
    bas = _ilk_zaman(defter_dosya)
    if bas is not None:   # madde 733: panel döküm satırı (pozisyonlar · gerçekleşen · funding · komisyon)
        bd = birikim_dosya or os.path.join(os.path.dirname(dosya) or ".", "gelir_birikim.json")
        g = gf = None
        try:
            g = gelir_birikim(client, bas, simdi, bd)
            kayit["gelir_bas"] = {"bas": bas, "son": g["son_ms"] // 1000, **g["toplam"]}
        except Exception as ex:
            print(f"UYARI: gelir birikimi güncellenemedi: {ex}", file=sys.stderr)
        try:   # madde 744: gerçek oranlarla olsaydı (yalnız demo)
            gf = gercek_funding(client, bas, simdi, poz, os.path.join(os.path.dirname(dosya) or ".", "gercek_funding.json"))
            if gf is not None:
                kayit["gercek_funding"] = {"bas": bas, "toplam": gf["toplam"], "son": gf["son_ms"] // 1000}
        except Exception as ex:
            print(f"UYARI: gerçek oranlı funding güncellenemedi: {ex}", file=sys.stderr)
        try:   # madde 749: funding ödemeleri olaylar sayfasına
            fo = os.path.join(os.path.dirname(dosya) or ".", "funding_olay.json")
            dm = (g or {}).get("_yeni_funding") or []
            gr = (gf or {}).get("_yeni") or []
            if not os.path.exists(fo):   # ilk kurulum: son FUNDING_OLAY_GUN günün geçmişi
                ilk_ms = max(bas * 1000, int((simdi - FUNDING_OLAY_GUN * 86400) * 1000)); bit = int(simdi * 1000)
                dm, s_ = [], ilk_ms
                for _ in range(20):
                    r = client.client.futures_income_history(incomeType="FUNDING_FEE", startTime=s_, endTime=bit, limit=1000)
                    dm += [(int(x["time"]), x["symbol"], float(x["income"])) for x in r if x.get("symbol")]
                    if len(r) < 1000:
                        break
                    s_ = int(r[-1]["time"]) + 1
                gr = []
                if _veri_istemcisi(client) is not None and emir_db and os.path.exists(emir_db):
                    try:
                        gr = _gercek_gecmis(client, defter_dosya, emir_db, ilk_ms, bit)
                    except Exception as ex:
                        print(f"UYARI: gerçek-oran funding geçmişi kurulamadı: {ex}", file=sys.stderr)
            funding_olay_ekle(fo, simdi, dm, gr)
        except Exception as ex:
            print(f"UYARI: funding olayları yazılamadı: {ex}", file=sys.stderr)
    _atomik_yaz(dosya, kayit)
    try:   # madde 745: pozisyon geçmişi (olaylarda işlem sonrası ortalama)
        poz_gecmis_ekle(os.path.join(os.path.dirname(dosya) or ".", "anlik_poz.json"), simdi, poz)
    except Exception as ex:
        print(f"UYARI: pozisyon geçmişi yazılamadı: {ex}", file=sys.stderr)
    if emir_db:   # madde 745: emir dolumlarını 5 dk'da bir eşle (yalnız OKUMA; bot turu sonunu beklemesin)
        try:
            import defter_db
            if os.path.exists(emir_db):
                defter_db.emir_esle(client, db=emir_db, simdi=simdi, taze_sn=120, haric=("FELAKET", "TP", "KADEME"))
        except Exception as ex:
            print(f"UYARI: emir dolumları eşlenemedi: {ex}", file=sys.stderr)
    if os.getenv("CARRY_ANLIK_STOP", "1") != "0":   # madde 753: koşullu stop yakınlığı (saatte bir, salt okuma)
        try:
            stop_durum(client, poz, simdi, os.path.join(os.path.dirname(dosya) or ".", "stop_durum.json"), kayit["kitap"])
        except Exception as ex:
            print(f"UYARI: koşullu stop durumu ölçülemedi: {ex}", file=sys.stderr)
    if "gelir_bas" in kayit:   # madde 742: transfer bilinmeden nokta yazılmaz (yatırma eğride kâr gibi görünmesin)
        try:
            gun_egri_ekle(os.path.join(os.path.dirname(dosya) or ".", "anlik_gun.json"), simdi,
                          oz - float(kayit["gelir_bas"].get("TRANSFER", 0.0) or 0.0))
        except Exception as ex:
            print(f"UYARI: gün içi kitap noktası yazılamadı: {ex}", file=sys.stderr)
    return kayit


def main() -> int:
    try:
        k = yaz()
    except Exception as ex:
        print(f"anlık görüntü alınamadı: {ex}", file=sys.stderr)
        return 1
    _f = (k.get("gelir_bas") or {}).get("FUNDING_FEE"); _g = (k.get("gercek_funding") or {}).get("toplam")
    print(f"{len(k['pozisyonlar'])} pozisyon · gerçekleşmemiş {k['gerceklesmemis_top']:+.2f} $ · kitap {k['kitap']:,.2f} $"
          + (f" · funding {_f:+.4f} $" if _f is not None else "") + (f" · gerçek oranlarla {_g:+.4f} $" if _g is not None else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
