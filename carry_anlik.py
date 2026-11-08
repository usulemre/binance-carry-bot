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

from carry_gunluk_defter import DEFTER_DOSYA, DEFTER_KLASOR, _pozisyonlar

ANLIK_DOSYA = os.path.join(DEFTER_KLASOR, "anlik.json")
BIRIKIM_DOSYA = os.path.join(DEFTER_KLASOR, "gelir_birikim.json")
GUN_DOSYA = os.path.join(DEFTER_KLASOR, "anlik_gun.json")
ORTUSME_MS = 10 * 60 * 1000   # geç düşen gelir kaydı kaçmasın: son 10 dk yeniden sorulur, tranId ile tekilleşir
GERCEK_DOSYA = os.path.join(DEFTER_KLASOR, "gercek_funding.json")
TOHUM_PENCERE_MS = 8 * 3600 * 1000   # tohum: gerçek funding anına en yakın demo funding kaydı bu kadar yakınsa pozisyon vardı sayılır
GUN_DEVIR_SN = 15 * 60        # önceki günün son noktası gün başına bu kadar yakınsa yeni günün açılış değeri olur


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
        b = {"bas_ms": bas_ms, "son_ms": bas_ms, "toplam": {}, "idler": {}}
    bit_ms = int(simdi * 1000)
    idler = dict(b.get("idler") or {})   # kimlik -> kayıt zamanı (ms); yalnız örtüşme penceresindekiler saklanır
    toplam = dict(b.get("toplam", {}))
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
        if len(r) < 1000:
            break
        s = int(r[-1]["time"]) + 1
    else:
        son = s - 1   # 50 sayfa yetmedi: kalanı sonraki çalışmada
    idler = {k: t for k, t in idler.items() if t >= son - 2 * ORTUSME_MS}
    b = {"bas_ms": bas_ms, "son_ms": son, "toplam": {k: round(v, 6) for k, v in toplam.items()}, "idler": idler}
    _atomik_yaz(dosya, b)
    return b


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
    for sem, p in poz.items():
        for x in v.futures_funding_rate(symbol=sem, startTime=son + 1, endTime=bit_ms, limit=10):
            fiyat = float(x.get("markPrice") or 0) or float(p.get("isaret") or 0)
            top += -float(p["miktar"]) * fiyat * float(x["fundingRate"])
    b.update(son_ms=bit_ms, toplam=round(top, 6))
    _atomik_yaz(dosya, b)
    return b


def yaz(client=None, simdi: float | None = None, dosya: str = ANLIK_DOSYA,
        defter_dosya: str = DEFTER_DOSYA, birikim_dosya: str | None = None) -> dict:
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
    bas = _ilk_zaman(defter_dosya)
    if bas is not None:   # madde 733: panel döküm satırı (pozisyonlar · gerçekleşen · funding · komisyon)
        bd = birikim_dosya or os.path.join(os.path.dirname(dosya) or ".", "gelir_birikim.json")
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
    _atomik_yaz(dosya, kayit)
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
    print(f"{len(k['pozisyonlar'])} pozisyon · gerçekleşmemiş {k['gerceklesmemis_top']:+.2f} $ · kitap {k['kitap']:,.2f} $")
    return 0


if __name__ == "__main__":
    sys.exit(main())
