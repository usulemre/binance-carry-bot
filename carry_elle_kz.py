# -*- coding: utf-8 -*-
"""MADDE 849 — ELLE KÂR / ZARAR botun muhasebesinden AYRILIR.
MADDE 851 (2026-11-23) KURAL DEĞİŞTİ: kullanıcı "blessi yapmamış gibi geri al" → botun aralık başındaki adedi BOTTA kalır (devir yok);
kullanıcının payı yalnız kendi dolumları (bkz. aralik_hesapla). Aşağıdaki "devir" anlatımı eski kuraldır (849), artık devir = 0.

Kullanıcı (2026-11-23): "ana bot bakiyesi 2 bin dolarlık işlemde, ben ekstra kendim elle alımlar yapıyorum; panelde % düşüş
2 bin dolardan sayılıyor, bu yanlış değil mi" → seçim: TAM AYIR (panel + botun sermayesi + günlük getiri), devralınan kısım
DEVİR ANINA KADAR BOTUN.

TANIM
  Elle aralık = bir sembolün kullanıcıda olduğu dönem: kullanıcının İLK dolumu → bot sembolü geri bırakana kadar
  (carry_elle "birak" olayı). O aralıktaki her şey (gerçekleşen, funding, komisyon, açık K/Z) elle sayılır, TEK istisna:
  bottan devralınan adet, devir anındaki fiyattan (kullanıcının ilk dolum fiyatı) kullanıcıya "satılmış" kabul edilir —
  o ana kadarki kâr/zararı (`devir`) botundur.

  Hesap: devralınan lot (adet = bugünkü/kapanıştaki adet − aralıktaki dolumların toplamı, fiyat = ilk dolum fiyatı) ile
  başlanır, aralıktaki BÜTÜN dolumlar ortalama maliyetle yeniden oynatılır:
      elle_kz = oynatılmış gerçekleşen + oynatılmış açık K/Z + funding + komisyon
      devir   = (Binance gerçekleşen + Binance açık K/Z) − (oynatılmış gerçekleşen + oynatılmış açık K/Z)
  Botun özkaynağı = hesap özkaynağı − Σ elle_kz (bütün aralıklar). Bot boyutlaması, günlük getiri, panel yüzdeleri bunu kullanır.

DOSYA  defter/elle_kz.json  {"aralik": {sembol: [{bas, ilk_fiyat, bit, son, R, F, C, U, kz, devir, devr_adet}, ...]},
                             "toplam": Σkz, "zaman": s}
  Kapanmış aralık bir kez hesaplanır ve dondurulur (son=True). Açık aralık her çağrıda yeniden hesaplanır.

GÜVENLİK
  Borsa okunamazsa son bilinen değer döner (kayıttaki toplam); hiç kayıt yoksa 0 (eski davranış). Bir sembol okunamazsa
  o sembolün son bilinen değeri korunur.
"""
from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

DOSYA = os.getenv("CARRY_ELLE_KZ", os.path.join("defter", "elle_kz.json"))
PENCERE_MS = 2 * 3600 * 1000
"""İlk kullanıcı dolumu, işaret / panel zamanından en çok bu kadar önce aranır (elle kontrolü saatte bir)."""
HAFTA_MS = 7 * 86400 * 1000 - 1000


def _oku(dosya: str) -> dict:
    try:
        with open(dosya, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict):
            d.setdefault("aralik", {})
            return d
    except (OSError, ValueError):
        pass
    return {"aralik": {}}


def _yaz(dosya: str, d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(dosya) or ".", exist_ok=True)
        tmp = dosya + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, dosya)
    except OSError as e:
        logger.warning("elle K/Z kaydı yazılamadı: %s", e)


def toplam_oku(dosya: str = DOSYA) -> float:
    """API çağırmadan son bilinen elle K/Z toplamı (yoksa 0)."""
    try:
        return float(_oku(dosya).get("toplam") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _olaylar(olay_dosya: str | None) -> dict:
    """{sembol: {"isaret": [t...], "birak": [t...]}}"""
    out = {}
    if not olay_dosya:
        return out
    try:
        with open(olay_dosya, encoding="utf-8") as f:
            for satir in f:
                try:
                    o = json.loads(satir)
                except ValueError:
                    continue
                if o.get("olay") in ("isaret", "birak") and o.get("sembol"):
                    out.setdefault(o["sembol"], {"isaret": [], "birak": []})[o["olay"]].append(int(o.get("t") or 0))
    except OSError:
        pass
    return out


def _dolumlar(ic, sem: str, bas: int, bit: int) -> list:
    """Hesabın bu semboldeki dolumları [bas, bit] (7 günlük pencerelerle, tekilleştirilmiş, zamana göre)."""
    gor, out, s = set(), [], int(bas)
    while s <= bit:
        e = min(bit, s + HAFTA_MS)
        T = ic.futures_account_trades(symbol=sem, startTime=s, endTime=e, limit=1000) or []
        for t in T:
            k = t.get("id")
            if k in gor:
                continue
            gor.add(k); out.append(t)
        if len(T) >= 1000:
            yeni = int(T[-1].get("time") or s)
            s = yeni if yeni > s else s + 1
        else:
            s = e + 1
    out.sort(key=lambda t: (int(t.get("time") or 0), int(t.get("id") or 0)))
    return out


def _funding(ic, sem: str, bas: int, bit: int) -> float:
    top, s = 0.0, int(bas)
    for _ in range(50):
        r = ic.futures_income_history(symbol=sem, incomeType="FUNDING_FEE", startTime=s, endTime=bit, limit=1000) or []
        top += sum(float(x.get("income") or 0) for x in r)
        if len(r) < 1000:
            break
        s = int(r[-1].get("time") or s) + 1
    return top


def _ilk_kullanici_dolumu(ic, sem: str, alt: int, ust: int) -> tuple[int, float] | None:
    """[alt, ust] aralığında dolmuş İLK kullanıcı emrinin (zaman, ortalama fiyat)'ı."""
    import carry_elle
    E = ic.futures_get_all_orders(symbol=sem, startTime=int(alt), limit=500) or []
    K = [o for o in E if carry_elle._dolan(o) > 0 and carry_elle.emir_sahibi(o) == "kullanici"
         and alt <= int(o.get("time") or o.get("updateTime") or 0) <= ust]
    if not K:
        return None
    o = min(K, key=lambda o: int(o.get("time") or o.get("updateTime") or 0))
    f = float(o.get("avgPrice") or 0) or float(o.get("price") or 0)
    return (int(o.get("time") or o.get("updateTime")), f) if f > 0 else None


def aralik_hesapla(ic, sem: str, a: dict, poz: tuple | None, simdi_ms: int) -> dict:
    """Bir aralığın elle K/Z'si. poz = (adet, binance_açık_kz, işaret_fiyatı, binance_giriş) — açık aralıkta borsadaki pozisyon.

    MADDE 851 kuralı (kullanıcı: "blessi yapmamış gibi geri al", bota geri ver): botun aralık başındaki adedi BOTTA KALIR — kullanıcıya
    geçmez. Kullanıcının payı yalnız aralıktaki dolumların sıfırdan oynatılmasıdır (bot elle coine emir göndermez). Botun payı =
    borsadaki adet − kullanıcının adedi; açık K/Z'si borsanınkinden kullanıcınınki düşülerek. Funding adet oranıyla bölünür."""
    bit = int(a["bit"]) if a.get("bit") else simdi_ms
    T = _dolumlar(ic, sem, int(a["bas"]), bit)
    acik_ = bool(poz) and not a.get("bit")
    adet_son = float(poz[0]) if acik_ else 0.0
    q, ort, gercek, R, C = 0.0, 0.0, 0.0, 0.0, 0.0
    for t in T:
        s_ = float(t.get("qty") or 0) * (1 if t.get("side") == "BUY" else -1)
        p = float(t.get("price") or 0)
        R += float(t.get("realizedPnl") or 0)
        kom = float(t.get("commission") or 0)
        if str(t.get("commissionAsset") or "USDT").upper() in ("USDT", "USDC", "BUSD", "FDUSD", ""):
            C -= kom
        if abs(q) < 1e-12 or (s_ > 0) == (q > 0):
            ort = (abs(q) * ort + abs(s_) * p) / (abs(q) + abs(s_)) if abs(q) + abs(s_) > 0 else p
            q += s_
        else:
            kap = min(abs(s_), abs(q))
            gercek += kap * (p - ort) * (1 if q > 0 else -1)
            yeni = q + s_
            if abs(yeni) > 1e-12 and (yeni > 0) != (q > 0):
                ort = p
            q = yeni
    if abs(q) < 1e-9:
        q = 0.0
    q_bot = adet_son - q if acik_ else 0.0
    if abs(q_bot) < 1e-9:
        q_bot = 0.0
    U = Uo = 0.0
    e_bot = None
    if acik_:
        U = float(poz[1])
        isaret = float(poz[2] or 0) or None
        Uo = q * (isaret - ort) if (isaret and q) else (U if q_bot == 0 else 0.0)
        g = float(poz[3]) if len(poz) > 3 and poz[3] else 0.0
        if q_bot and g > 0:
            e_bot = (adet_son * g - q * ort) / q_bot
            e_bot = e_bot if e_bot > 0 else None
    F = _funding(ic, sem, int(a["bas"]), bit)
    pay = 1.0 if not (acik_ and adet_son) else q / adet_son
    Fk = F * pay
    kz = gercek + Uo + Fk + C
    return {**a, "R": round(R, 6), "F": round(F, 6), "C": round(C, 6), "U": round(U, 6),
            "Rk": round(gercek, 6), "Fk": round(Fk, 6), "Uk": round(Uo, 6), "q_k": round(q, 10), "ort_k": ort if q else None,
            "q_bot": round(q_bot, 10), "e_bot": e_bot, "U_bot": round(U - Uo, 6), "devr_adet": round(q_bot, 10),
            "kz": round(kz, 6), "devir": 0.0, "kural": "bota_geri"}


def guncelle(client, simdi: float | None = None, dosya: str = DOSYA, elle_dosya: str | None = None,
             olay_dosya: str | None = None, panel_dosya: str | None = None) -> dict:
    """Elle aralıklarını bulur / kapatır, K/Z'yi hesaplar, kaydı yazar ve döner. Hata olursa son kayıt döner."""
    import carry_elle
    elle_dosya = elle_dosya or os.getenv("CARRY_ELLE_DOSYA", "carry_elle.json")
    olay_dosya = olay_dosya or os.getenv("CARRY_ELLE_OLAY", "carry_elle_olay.jsonl")
    panel_dosya = panel_dosya or os.getenv("CARRY_ELLE_PANEL", os.path.join("defter", "carry_elle_panel.json"))
    simdi_ms = int((simdi or time.time()) * 1000)
    st = _oku(dosya)
    ic = client.client
    try:
        pozlar = {}
        for p in client.get_open_positions():
            a = float(p.get("positionAmt") or 0)
            if abs(a) > 1e-12:
                u = float(p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0)
                m = float(p.get("markPrice") or 0)
                if m <= 0 and float(p.get("entryPrice") or 0) > 0:
                    m = float(p["entryPrice"]) + u / a
                pozlar[p["symbol"]] = (a, u, m, float(p.get("entryPrice") or 0))
    except Exception as e:
        logger.warning("elle K/Z: pozisyonlar okunamadı (%s) — son bilinen değer", e)
        return st
    kayit = carry_elle.kayit_oku(elle_dosya)
    elle = kayit.get("elle") or {}
    panel = carry_elle.panel_okuma(panel_dosya)
    acik_set = set(elle) | carry_elle.panel_isaretleri(panel_dosya, elle_dosya, simdi_ms)
    O = _olaylar(olay_dosya)
    A = st["aralik"]
    # 1) kullanıcıda olmayan açık aralıkları kapat (bırakma zamanı = bas'tan sonraki ilk "birak" olayı)
    for sem, L in A.items():
        for a in L:
            if not a.get("bit") and sem not in acik_set:
                b = [t for t in (O.get(sem) or {}).get("birak", []) if t >= int(a["bas"])]
                a["bit"] = min(b) if b else simdi_ms
                a.pop("son", None)
    # 2) yeni elle semboller için aralık aç
    for sem in sorted(acik_set):
        L = A.setdefault(sem, [])
        if any(not a.get("bit") for a in L):
            continue
        adaylar = [int((elle.get(sem) or {}).get("t") or 0), int(panel.get(sem) or 0)]
        adaylar += [t for t in (O.get(sem) or {}).get("isaret", [])]
        onceki = max([int(a["bit"]) for a in L if a.get("bit")] + [int((kayit.get("birakilan") or {}).get(sem, 0))] + [0])
        adaylar = [t for t in adaylar if t > onceki]
        if not adaylar:
            continue
        alt = max(min(adaylar) - PENCERE_MS, onceki + 1)
        try:
            ilk = _ilk_kullanici_dolumu(ic, sem, alt, simdi_ms)
        except Exception as e:
            logger.warning("elle K/Z: %s emir geçmişi okunamadı (%s)", sem, e)
            continue
        if ilk is None:
            continue     # panel işareti var ama dolum yok (henüz) — bir sonraki çağrıda
        L.append({"bas": ilk[0], "ilk_fiyat": ilk[1], "bit": None})
    # 3) hesapla (kapanmışlar bir kez)
    for sem, L in A.items():
        for i, a in enumerate(L):
            if a.get("son") and a.get("kural") == "bota_geri":
                continue
            try:
                L[i] = aralik_hesapla(ic, sem, a, pozlar.get(sem), simdi_ms)
                if a.get("bit"):
                    L[i]["son"] = True
            except Exception as e:
                logger.warning("elle K/Z: %s hesaplanamadı (%s) — son bilinen değer", sem, e)
    st["toplam"] = round(sum(float(a.get("kz") or 0) for L in A.values() for a in L), 4)
    st["acik_sembol"] = sorted(s for s, L in A.items() if any(not a.get("bit") for a in L))
    st["zaman"] = int(simdi_ms / 1000)
    _yaz(dosya, st)
    return st


def ozet(st: dict, bas_s: int | None = None) -> dict:
    """Panel için: bas_s (başlangıç) sonrası aralıkların toplamları — kz, gerçekleşen (Binance), funding, komisyon,
    açık (Binance), devir; ayrıca sembol başına."""
    T = {"kz": 0.0, "Rk": 0.0, "Fk": 0.0, "C": 0.0, "Uk": 0.0}
    S = {}
    for sem, L in (st.get("aralik") or {}).items():
        for a in L:
            if bas_s is not None and int(a.get("bas") or 0) < bas_s * 1000:
                continue
            for k in T:
                v = float(a.get(k) or 0); T[k] += v
                S.setdefault(sem, {kk: 0.0 for kk in T})[k] += v
    return {"toplam": {k: round(v, 4) for k, v in T.items()}, "sembol": {s: {k: round(v, 4) for k, v in d.items()} for s, d in S.items()},
            "acik_sembol": st.get("acik_sembol") or [], "zaman": st.get("zaman")}


def guncel_toplam(client, en_eski_sn: float = 300.0, dosya: str = DOSYA, simdi: float | None = None) -> float:
    """Kayıt `en_eski_sn`'den tazeyse onu (carry_anlik 5 dk'da bir günceller), değilse hesaplayıp döner. Hata: son bilinen / 0."""
    simdi = simdi or time.time()
    st = _oku(dosya)
    if st.get("zaman") and simdi - float(st["zaman"]) < en_eski_sn:
        return float(st.get("toplam") or 0.0)
    try:
        return float(guncelle(client, simdi=simdi, dosya=dosya).get("toplam") or 0.0)
    except Exception as e:
        logger.warning("elle K/Z hesaplanamadı (%s) — son bilinen değer", e)
        return float(st.get("toplam") or 0.0)


def acik(ortam: dict | None = None) -> bool:
    """Elle takip açık mı (CARRY_ELLE=1)? Kapalıysa elle K/Z hiç hesaplanmaz (eski davranış)."""
    return str((ortam or os.environ).get("CARRY_ELLE", "0")).strip() == "1"


def sabit_mi(dosya: str = DOSYA) -> bool:
    """MADDE 851: elle takip kapalı (CARRY_ELLE=0) ama geçmiş elle K/Z kaydı var mı? (taşıma sonrası: al-sat ayrı hesapta; bot hesabında
    kalan elle K/Z SABİT bir düzeltme olarak botun özkaynağından düşülmeye devam eder)"""
    st = _oku(dosya)
    return bool(st.get("aralik")) and st.get("toplam") is not None


def etkin_toplam(client, dosya: str = DOSYA, simdi: float | None = None) -> float | None:
    """Bot / defter için: elle açıkken güncel toplam, kapalıyken sabit kayıt; ikisi de yoksa None (düzeltme yok)."""
    if acik():
        return guncel_toplam(client, dosya=dosya, simdi=simdi)
    return toplam_oku(dosya) if sabit_mi(dosya) else None


def dondur(st: dict, simdi_ms: int, dosya: str = DOSYA) -> dict:
    """MADDE 851 taşıma: bütün açık aralıklar ŞU AN kapanır, son hesaplanan değerleriyle dondurulur (yeniden hesaplanmaz)."""
    for L in (st.get("aralik") or {}).values():
        for a in L:
            if not a.get("bit"):
                a["bit"] = simdi_ms; a["son"] = True; a["kural"] = "bota_geri"; a["tasindi"] = True
    st["toplam"] = round(sum(float(a.get("kz") or 0) for L in st["aralik"].values() for a in L), 4)
    st["acik_sembol"] = []
    st["donduruldu"] = int(simdi_ms / 1000)
    _yaz(dosya, st)
    return st
