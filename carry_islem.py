# -*- coding: utf-8 -*-
"""MADDE 834 — PANELDEN ELLE İŞLEM KAPISI (ayrı servis: carry-islem, YALNIZ 127.0.0.1:8051).

Kullanıcı isteği (2026-11-22): "listeden panelden almak istiyorum, Binance sitesi karışık." Kullanıcı kararları: tek emir en fazla
200 $ (pozisyon büyüklüğü), her emirde İŞLEM PIN'i.

MİMARİ — panel YİNE ANAHTARSIZ:
  * Panel (panel.py) anahtar görmez, .env'deki anahtarları okumaz (madde 671 aynen). Panel /api/islem/* isteklerini bu servise
    iletir; bu servis botla aynı anahtarı (EnvironmentFile + şifreli ImportCredential, config.py) kullanır ve yalnız 127.0.0.1'de dinler.
  * Her EMİR / KAPAT / TP-SL / İPTAL isteği İŞLEM PIN'i ister (CARRY_ISLEM_PIN, .env; en az 6 karakter). 5 yanlış PIN → 15 dk kilit.
  * Kapalı başlar: CARRY_PANEL_ISLEM=1 + PIN yoksa hiçbir emir kabul edilmez. Canlı hesapta ayrıca CARRY_ISLEM_CANLI=1 gerekir.
  * CARRY_ELLE=1 değilse emir REDDEDİLİR: elle takip kapalıyken bot bir sonraki turda kullanıcının işlemini geri alırdı (madde 830).
  * Tek emir ≤ CARRY_ISLEM_MAX_USD (200 $) pozisyon büyüklüğü; yalnız USDT perpetual TRADING sözleşme; limit fiyatı işaret fiyatının
    ±%20'si içinde; TP / SL yön mantığı denetlenir (long: SL < fiyat < TP).
  * Bütün emirler `panel_` önekli clientOrderId / clientAlgoId ile gider (python-binance'in bot öneki EZİLİR) -> bot bunları kullanıcı
    işlemi sayar, coini kullanıcıya bırakır (madde 830 / 831). Kapat / iptal yalnız `panel_` önekli emirlere dokunur.
  * Kaldıraç / teminat tipi DEĞİŞTİRİLMEZ (hesaptaki mevcut ayar).
  * Her işlem defter/panel_islem.jsonl'a yazılır ve Telegram'a bildirilir. Yanıtlarda anahtar / PIN yoktur.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import re
import secrets
import sys
import threading
import time

logger = logging.getLogger("carry_islem")

ONEK = "panel_"
PARCA_ONEK = "panel_P"   # madde 863: alım parçasına bağlı TP / stop (clientAlgoId: panel_P<parça>_<T|S>_<rastgele>)


def _parca_cid(pid: str, tur: str) -> str:
    return f"{PARCA_ONEK}{pid}_{tur}_{secrets.token_hex(2)}"[:36]


def _algo_parca(o: dict) -> str | None:
    """Algo emri bir alım parçasına bağlıysa parça kimliği, değilse None."""
    c = str(o.get("clientAlgoId") or "")
    if not c.startswith(PARCA_ONEK):
        return None
    return c[len(PARCA_ONEK):].rsplit("_", 2)[0] or None
IZ_MIN, IZ_MAX = 0.1, 10.0   # madde 901: iz süren stop geri dönüş oranı (%); Binance 0,1–20 kabul eder, panel 10 ile sınırlar


def _iz_mi(o: dict) -> bool:
    """Algo emri iz süren stop (TRAILING_STOP_MARKET) mu?"""
    return str(o.get("orderType") or o.get("type") or "").startswith("TRAILING")


SEMBOL_RE = re.compile(r"^[A-Z0-9]{2,20}USDT$")
MIN_USD = 5.0
LIMIT_BANT = 0.20
KILIT_DENEME, KILIT_SN = 5, 900


def _env_bool(ad: str) -> bool:
    return os.getenv(ad, "0").strip().lower() in ("1", "true", "evet")


def ayarlar() -> dict:
    return {"acik": _env_bool("CARRY_PANEL_ISLEM"), "pin": os.getenv("CARRY_ISLEM_PIN", "").strip(),
            "max_usd": float(os.getenv("CARRY_ISLEM_MAX_USD", "200") or 200), "mod": os.getenv("BINANCE_MODE", "demo"),
            "canli_izin": _env_bool("CARRY_ISLEM_CANLI"), "elle": os.getenv("CARRY_ELLE", "0") not in ("0", "false", "False", ""),
            "defter": os.getenv("CARRY_ISLEM_DEFTER", os.path.join("defter", "panel_islem.jsonl")),
            "elle_panel": os.getenv("CARRY_ELLE_PANEL", os.path.join("defter", "carry_elle_panel.json")),
            "elle_dosya": os.getenv("CARRY_ELLE_DOSYA", "carry_elle.json"),
            "elle_olay": os.getenv("CARRY_ELLE_OLAY", "carry_elle_olay.jsonl"),
            "dilim": os.getenv("CARRY_DILIM_LOG", "carry_dilimler.json"),
            # MADDE 851: AL-SAT AYRI HESAP — anahtar varsa bütün işlemler o hesapta; botla hiçbir bağ yok (elle işareti yazılmaz).
            # Yoksa GEÇİŞ: bot hesabında yalnız mevcut elle pozisyonlar küçültülür / kapatılır, TP-SL konur; yeni pozisyon açılmaz.
            "ayri": bool(os.getenv("ALSAT_API_KEY", "").strip() and os.getenv("ALSAT_API_SECRET", "").strip()),
            "alsat_mod": os.getenv("ALSAT_MODE", "").strip() or os.getenv("BINANCE_MODE", "demo"),
            "anlik": os.getenv("CARRY_ALSAT_ANLIK", os.path.join("defter", "alsat_anlik.jsonl")),
            "parca": os.getenv("CARRY_ALSAT_PARCA", os.path.join("defter", "alsat_parca.json")),   # madde 862
            "gecis_kisit": os.getenv("CARRY_ALSAT_GECIS", "1").strip() not in ("0", "false", "False"),
            "ayni_anahtar": bool(os.getenv("ALSAT_API_KEY", "").strip()) and os.getenv("ALSAT_API_KEY", "").strip() == os.getenv("BINANCE_API_KEY", "").strip()}


# madde 889: sık Binance vadeli hata kodları -> Türkçe, ne yapılacağını söyleyen mesaj (kod parantezde kalır)
BINANCE_TR = {
    -2019: "Teminat yetersiz: boştaki bakiye bu büyüklüğe yetmiyor. Tutarı düşür ya da başka pozisyonu küçült.",
    -4164: "Emir tutarı Binance'in bu coin için en düşük sınırının altında. Tutarı artır.",
    -2022: "Azaltma emri reddedildi: pozisyon zaten kapanmış ya da adet pozisyondan büyük olabilir. Pozisyonu yenileyip kontrol et.",
    -2021: "TP / stop fiyatı şimdiki fiyatı çoktan geçmiş; emir hemen tetiklenirdi. Fiyatı güncelleyip tekrar dene.",
    -4131: "Fiyat Binance'in izin verdiği bandın dışında (piyasa çok hızlı ya da derinlik az). Limit fiyatını şimdiki fiyata yaklaştır ya da tutarı küçült.",
    -1111: "Adet ya da fiyat bu coinin hassasiyetine uymuyor. Değeri biraz değiştirip tekrar dene.",
    -4005: "Adet bu coin için izin verilen en yüksek değeri aşıyor. Tutarı küçült.",
    -4003: "Adet sıfırdan büyük olmalı.",
    -1021: "Sunucu saati Binance ile uyuşmadı. Birkaç saniye sonra tekrar dene.",
    -1003: "Binance istek sınırı aşıldı. Bir dakika bekleyip tekrar dene.",
    -4045: "Bu coinde açık koşullu emir (TP / stop) sayısı sınıra ulaştı. Eski emirleri silip tekrar dene.",
    -2011: "Emir bulunamadı: dolmuş ya da iptal edilmiş olabilir. Listeyi yenile.",
    -2013: "Emir bulunamadı: dolmuş ya da iptal edilmiş olabilir. Listeyi yenile.",
    -4061: "Pozisyon yönü ayarı uyumsuz (hesapta hedge modu açık olabilir; panel tek yönlü mod bekler).",
    -5022: "Post-only emir hemen dolacağı için reddedildi. Fiyatı değiştir ya da piyasa emri kullan.",
    -4140: "Bu coin şu an işleme kapalı.",
    -1013: "Emir Binance'in sınır kurallarına uymuyor (adet / fiyat / tutar). Değerleri kontrol et.",
}


def binance_turkce(m: str) -> str:
    """'APIError(code=-2019): Margin is insufficient.' -> Türkçe açıklama + (Binance -2019). Tanınmayan kod: ham mesaj."""
    k = re.search(r"code=(-?\d+)", m or "")
    if k and int(k.group(1)) in BINANCE_TR:
        return f"{BINANCE_TR[int(k.group(1))]} (Binance {k.group(1)})"
    return f"Binance: {m}"


class Hata(Exception):
    def __init__(self, mesaj: str, kod: int = 400):
        super().__init__(mesaj); self.mesaj, self.kod = mesaj, kod


def _cid() -> str:
    return f"{ONEK}{int(time.time() * 1000)}_{secrets.token_hex(3)}"


class Kapi:
    """İş mantığı (Flask'tan bağımsız, test edilebilir). `client` = ExchangeClient benzeri (client.client = python-binance)."""

    def __init__(self, client, ayar: dict | None = None, bildir=None, saat=time.time):
        self.c, self.ic = client, client.client
        self.ayar = ayar or ayarlar()
        self.bildir = bildir
        self.saat = saat
        self._bilgi, self._bilgi_t = None, 0.0
        self._yanlis: list[float] = []
        self._kilit = threading.Lock()
        self._parca_onbellek: dict = {}
        self._acilis_t: dict = {}; self._poz_gelir_onb = None   # madde 902

    # ------------------------------------------------------------ denetimler
    def durum(self) -> dict:
        a = self.ayar
        neden = self._kapali_neden()
        sem = []
        if neden is None:      # madde 847: hesapta işlem gören sözleşmeler (demo ortamında gerçek piyasadaki her coin yok)
            try:
                self._sembol_bilgi("BTCUSDT", sessiz=True)
                sem = sorted(self._bilgi or {})
            except Exception:
                sem = []
        return {"acik": neden is None, "neden": neden, "mod": a["mod"], "max_usd": a["max_usd"], "pin_var": bool(a["pin"]), "semboller": sem,
                "ayri": bool(a.get("ayri")), "gecis": not a.get("ayri") and bool(a.get("gecis_kisit"))}

    def _kapali_neden(self) -> str | None:
        a = self.ayar
        if not a["acik"]:
            return "panelden işlem kapalı (CARRY_PANEL_ISLEM=1 değil)"
        if len(a["pin"]) < 6:
            return "işlem PIN'i ayarlı değil (CARRY_ISLEM_PIN, en az 6 karakter)"
        if a["mod"] == "live" and not a["canli_izin"]:
            return "canlı hesapta panelden işlem için ayrıca CARRY_ISLEM_CANLI=1 gerekir"
        if a.get("ayni_anahtar"):
            return "al-sat anahtarı botun anahtarıyla AYNI — ayrı bir hesabın anahtarı gerekir"
        if not a.get("ayri") and not a["elle"]:
            return "elle takip kapalı (CARRY_ELLE=1 değil) — bot işlemini bir sonraki turda geri alırdı"
        return None

    def _pin(self, pin) -> None:
        n = self._kapali_neden()
        if n:
            raise Hata(n, 403)
        simdi = self.saat()
        self._yanlis = [t for t in self._yanlis if simdi - t < KILIT_SN]
        if len(self._yanlis) >= KILIT_DENEME:
            raise Hata(f"çok fazla yanlış PIN — {int((KILIT_SN - (simdi - self._yanlis[0])) / 60) + 1} dk kilitli", 429)
        if not hmac.compare_digest(str(pin or "").encode(), self.ayar["pin"].encode()):
            self._yanlis.append(simdi)
            raise Hata(f"PIN yanlış ({KILIT_DENEME - len(self._yanlis)} deneme kaldı)", 403)
        self._yanlis.clear()

    def _sembol_bilgi(self, sem: str, sessiz: bool = False) -> dict:
        if not SEMBOL_RE.match(sem or ""):
            raise Hata("geçersiz sembol")
        eski = self._bilgi is None or self.saat() - self._bilgi_t > 600
        if not eski and sem not in self._bilgi and self.saat() - self._bilgi_t > 60:
            eski = True       # madde 847: yeni listelenen coin için önbelleği bir kez tazele
        if eski:
            from exchange_client import _adim, _tick_ondalik
            b = {}
            for s in self.ic.futures_exchange_info()["symbols"]:
                if s.get("contractType") == "PERPETUAL" and s.get("quoteAsset") == "USDT" and s.get("status") == "TRADING":
                    mn = next((float(f.get("notional") or f.get("minNotional") or 0) for f in s.get("filters", [])
                               if f.get("filterType") == "MIN_NOTIONAL"), MIN_USD)
                    b[s["symbol"]] = {"quantity_precision": s.get("quantityPrecision", 3), "price_precision": _tick_ondalik(s),
                                      "step": _adim(s, "LOT_SIZE"), "piyasa_step": _adim(s, "MARKET_LOT_SIZE") or _adim(s, "LOT_SIZE"),
                                      "min_usd": max(MIN_USD, mn)}
            self._bilgi, self._bilgi_t = b, self.saat()
        if sem not in self._bilgi:
            if sessiz:
                return {}
            ad = sem.replace("USDT", "")
            if self.ayar["mod"] != "live":
                raise Hata(f"{ad} demo hesapta işlem görmüyor. Binance'in demo ortamında gerçek piyasadaki her coin yok "
                           f"(özellikle yeni listelenenler); grafik ve fiyat gerçek piyasadan geliyor.", 404)
            raise Hata(f"{ad} bu hesapta işlem gören bir USDT perpetual sözleşme değil.", 404)
        return self._bilgi[sem]

    def _isaret(self, sem: str) -> float:
        f = float(self.ic.futures_mark_price(symbol=sem)["markPrice"])
        if not f > 0:
            raise Hata("işaret fiyatı okunamadı", 502)
        return f

    def _pozisyon(self, sem: str) -> dict:
        for p in self.c.get_open_positions():
            if p.get("symbol") == sem and abs(float(p.get("positionAmt") or 0)) > 0:
                return {"adet": float(p["positionAmt"]), "giris": float(p.get("entryPrice") or 0),
                        "kz": float(p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0),
                        "likidasyon": float(p.get("liquidationPrice") or 0)}
        return {"adet": 0.0, "giris": 0.0, "kz": 0.0, "likidasyon": 0.0}

    @staticmethod
    def _fiyat_yuvarla(f: float, b: dict) -> str:
        return f"{f:.{int(b['price_precision'])}f}"

    def _yon(self, yon) -> str:
        y = str(yon or "").upper()
        if y not in ("L", "S"):
            raise Hata("yön L (long) ya da S (short) olmalı")
        return y

    def _tpsl_denetle(self, y: str, ref: float, tp, sl) -> tuple:
        tp = float(tp) if tp not in (None, "", 0, "0") else None
        sl = float(sl) if sl not in (None, "", 0, "0") else None
        for ad, v in (("TP", tp), ("SL", sl)):
            if v is not None and not v > 0:
                raise Hata(f"{ad} fiyatı geçersiz")
        if y == "L":
            if tp is not None and tp <= ref:
                raise Hata("long'da TP fiyatın ÜSTÜNDE olmalı")
            if sl is not None and sl >= ref:
                raise Hata("long'da stop fiyatın ALTINDA olmalı")
        else:
            if tp is not None and tp >= ref:
                raise Hata("short'ta TP fiyatın ALTINDA olmalı")
            if sl is not None and sl <= ref:
                raise Hata("short'ta stop fiyatın ÜSTÜNDE olmalı")
        return tp, sl

    # ------------------------------------------------------------ önizleme
    def onizle(self, d: dict) -> dict:
        from exchange_client import adet_yuvarla
        sem = str(d.get("sembol") or "").upper()
        b = self._sembol_bilgi(sem)
        y = self._yon(d.get("yon"))
        tip = str(d.get("tip") or "MARKET").upper()
        if tip not in ("MARKET", "LIMIT"):
            raise Hata("emir tipi MARKET ya da LIMIT olmalı")
        try:
            usd = float(d.get("usd"))
        except (TypeError, ValueError):
            raise Hata("tutar ($) geçersiz")
        if usd > self.ayar["max_usd"] + 1e-9:
            raise Hata(f"tek emir en fazla {self.ayar['max_usd']:g} $ (CARRY_ISLEM_MAX_USD)")
        if usd < b["min_usd"]:
            raise Hata(f"tek emir en az {b['min_usd']:g} $ (Binance alt sınırı)")
        isaret = self._isaret(sem)
        fiyat = isaret
        if tip == "LIMIT":
            try:
                fiyat = float(d.get("fiyat"))
            except (TypeError, ValueError):
                raise Hata("limit fiyatı geçersiz")
            if not fiyat > 0 or abs(fiyat / isaret - 1) > LIMIT_BANT:
                raise Hata(f"limit fiyatı işaret fiyatının ±%{int(LIMIT_BANT * 100)}'si içinde olmalı (işaret {isaret:g})")
        adet = adet_yuvarla(usd / fiyat, b, piyasa=(tip == "MARKET"), asagi=True)
        if adet <= 0 or adet * fiyat < b["min_usd"] * 0.999:
            raise Hata(f"bu tutarla en küçük adım altında kalıyor (en az {b['min_usd']:g} $)")
        tp, sl = self._tpsl_denetle(y, fiyat, d.get("tp"), d.get("sl"))
        poz = self._pozisyon(sem)
        return {"sembol": sem, "yon": y, "tip": tip, "adet": adet, "fiyat": fiyat, "isaret": isaret, "usd": round(adet * fiyat, 4),
                "tp": tp, "sl": sl, "pozisyon": poz, "mod": self.ayar["mod"],
                "not": "TP/SL limit emri dolunca konulabilir (önce emir dolmalı)" if tip == "LIMIT" and (tp or sl) else ""}

    # ------------------------------------------------------------ işlemler
    def _kaydet(self, olay: dict) -> None:
        olay = {"t": int(self.saat() * 1000), **olay}
        try:
            yol = self.ayar["defter"]
            os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
            with open(yol, "a", encoding="utf-8") as f:
                f.write(json.dumps(olay, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("panel işlem defteri yazılamadı: %s", e)

    def _gecis_denetle(self, sem: str, yon: str | None = None, adet: float | None = None) -> None:
        """MADDE 851: ayrı hesap yokken bot hesabında yalnız ELLE coinlerde, pozisyonu BÜYÜTMEYEN işlem (CARRY_ALSAT_GECIS=1, varsayılan)."""
        if self.ayar.get("ayri") or not self.ayar.get("gecis_kisit"):
            return
        if sem not in self._elle_kumesi():
            raise Hata(f"{sem.replace('USDT', '')} botun coini. Al-sat hesabı bağlanana kadar bot hesabında yalnız mevcut elle pozisyonlarına "
                       f"işlem yapılabilir.", 403)
        if yon is None:
            return
        p = self._kullanici_adet(sem)
        kucultur = p != 0 and ((yon == "S") == (p > 0)) and adet is not None and adet <= abs(p) + 1e-12
        if not kucultur:
            raise Hata("Al-sat hesabı bağlanana kadar yeni pozisyon açılmıyor ve mevcut pozisyon büyütülmüyor; yalnız küçültebilir / "
                       "kapatabilirsin.", 403)

    def _kullanici_adet(self, sem: str) -> float:
        """Geçişte kullanıcının bu coindeki payı (muhasebe: kendi dolumları); muhasebe yoksa borsadaki adedin tamamı."""
        m = self._muhasebe(sem)
        if m and m.get("q_k") is not None:
            return float(m["q_k"])
        return float(self._pozisyon(sem)["adet"] or 0)

    def _elle_isaret(self, sem: str) -> None:
        """MADDE 838: bot bir sonraki kontrolü beklemeden coini kullanıcıya bıraksın (tur sırasında emir gitmez)."""
        yol = self.ayar.get("elle_panel")
        if not yol or self.ayar.get("ayri"):
            return
        try:
            import carry_elle
            os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
            carry_elle.panel_yaz(yol, sem, int(self.saat() * 1000))
        except Exception as e:
            logger.warning("elle panel işareti yazılamadı %s: %s", sem, e)

    def _haber(self, metin: str) -> None:
        if self.bildir:
            try:
                self.bildir(metin)
            except Exception:
                pass

    def _acik_algolar(self, sem: str) -> list:
        f = getattr(self.ic, "futures_get_open_algo_orders", None)
        if f is None:
            return []
        r = f(symbol=sem)
        return (r.get("orders", r) if isinstance(r, dict) else r) or []

    def _panel_tpsl_iptal(self, sem: str, tum: bool = False, parca: str | None = None, iz: bool = False) -> int:
        """Panel TP/SL'lerini iptal eder. Varsayılan: yalnız pozisyon geneli TP / stop (iz süren stop'a dokunmaz). tum=True: parçalar ve
        iz süren dahil hepsi. parca=<id>: yalnız o parçanınki. iz=True: yalnız iz süren stop (madde 901)."""
        n = 0
        for o in self._acik_algolar(sem):
            p = _algo_parca(o)
            if iz:
                sec = p is None and _iz_mi(o)
            else:
                sec = (p == parca) if parca is not None else (tum or (p is None and not _iz_mi(o)))
            if str(o.get("clientAlgoId") or "").startswith(ONEK) and sec:
                try:
                    self.ic.futures_cancel_algo_order(symbol=sem, algoId=o["algoId"]); n += 1
                except Exception as e:
                    logger.warning("panel TP/SL iptal edilemedi %s %s: %s", sem, o.get("algoId"), e)
        return n

    def _tpsl_kur(self, sem: str, adet_poz: float, tp, sl, b: dict) -> list:
        """Mevcut panel TP/SL'lerini iptal edip pozisyonun TAMAMI için yeniden kurar (eklemeden sonra da doğru adet)."""
        from exchange_client import adet_yuvarla
        self._panel_tpsl_iptal(sem)
        out = []
        if not adet_poz:
            return out
        kapat_yon = "SELL" if adet_poz > 0 else "BUY"
        q = adet_yuvarla(abs(adet_poz), b, piyasa=True, asagi=True)
        for ad, tur, v in (("TP", "TAKE_PROFIT_MARKET", tp), ("SL", "STOP_MARKET", sl)):
            if v is None:
                continue
            e = self.ic.futures_create_algo_order(algoType="CONDITIONAL", symbol=sem, side=kapat_yon, type=tur,
                                                  triggerPrice=self._fiyat_yuvarla(v, b), quantity=q, reduceOnly="true",
                                                  workingType="MARK_PRICE", clientAlgoId=_cid())
            out.append({"tur": ad, "fiyat": v, "algoId": (e or {}).get("algoId")})
        return out

    def emir(self, d: dict) -> dict:
        with self._kilit:
            self._pin(d.get("pin"))
            o = self.onizle(d)
            sem, b = o["sembol"], self._sembol_bilgi(o["sembol"])
            self._gecis_denetle(sem, o["yon"], o["adet"])
            self._elle_isaret(sem)      # emirden ÖNCE: tur sürüyorsa bot bu coine dokunmasın
            yon = "BUY" if o["yon"] == "L" else "SELL"
            kw = dict(symbol=sem, side=yon, quantity=o["adet"], newClientOrderId=_cid())
            if o["tip"] == "LIMIT":
                kw.update(type="LIMIT", timeInForce="GTC", price=self._fiyat_yuvarla(o["fiyat"], b))
            else:
                kw.update(type="MARKET")
            e = self.ic.futures_create_order(**kw)
            sonuc = {"emir": {"orderId": e.get("orderId"), "durum": e.get("status"), "adet": o["adet"], "tip": o["tip"]}, "tpsl": []}
            if o["tip"] == "MARKET" and (o["tp"] or o["sl"]):
                poz = self._pozisyon(sem)
                try:
                    sonuc["tpsl"] = self._tpsl_kur(sem, poz["adet"], o["tp"], o["sl"], b)
                except Exception as ex:
                    sonuc["tpsl_hata"] = f"emir doldu ama TP/SL konamadı: {binance_turkce(str(ex)).removeprefix('Binance: ')}"
            elif o["tip"] == "MARKET":   # madde 835: eklemede mevcut panel TP / stop'u TOPLAM adede göre aynı fiyatlarla yeniden kur
                try:
                    self._tpsl_yeniden(sem, b)
                except Exception as ex:
                    sonuc["tpsl_hata"] = f"emir doldu ama mevcut TP/SL yeni adede göre güncellenemedi: {binance_turkce(str(ex)).removeprefix('Binance: ')}"
            self._kaydet({"olay": "emir", **{k: o[k] for k in ("sembol", "yon", "tip", "adet", "fiyat", "usd", "tp", "sl")},
                          "orderId": e.get("orderId"), "durum": e.get("status"), "tpsl_hata": sonuc.get("tpsl_hata")})
            ad = sem.replace("USDT", "")
            self._haber(f"🖐 PANEL: {ad} {'LONG' if o['yon'] == 'L' else 'SHORT'} {o['tip']} {o['usd']:.0f} $ (adet {o['adet']:g})"
                        + (f" · TP {o['tp']:g}" if o["tp"] else "") + (f" · SL {o['sl']:g}" if o["sl"] else "")
                        + (f" · ⚠️ {sonuc['tpsl_hata']}" if sonuc.get("tpsl_hata") else ""))
            return sonuc

    def _iz_kur(self, sem: str, adet_poz: float, oran: float, aktif, b: dict) -> dict | None:
        """MADDE 901: pozisyonun tamamı için iz süren stop (TRAILING_STOP_MARKET, reduceOnly, işaret fiyatı). Mevcut panel iz süreni silinir.
        aktif (activatePrice) geçerli değilse (fiyat çoktan geçtiyse) gönderilmez: iz hemen başlar."""
        from exchange_client import adet_yuvarla
        self._panel_tpsl_iptal(sem, iz=True)
        if not adet_poz or not oran:
            return None
        uzun = adet_poz > 0
        q = adet_yuvarla(abs(adet_poz), b, piyasa=True, asagi=True)
        kw = dict(algoType="CONDITIONAL", symbol=sem, side="SELL" if uzun else "BUY", type="TRAILING_STOP_MARKET", quantity=q,
                  callbackRate=f"{oran:.1f}", reduceOnly="true", workingType="MARK_PRICE", clientAlgoId=_cid())
        if aktif:
            isr = self._isaret(sem)
            if (uzun and aktif > isr) or (not uzun and aktif < isr):
                kw["activatePrice"] = self._fiyat_yuvarla(aktif, b)
            else:
                aktif = None
        e = self.ic.futures_create_algo_order(**kw)
        return {"tur": "IZ", "oran": round(oran, 1), "aktif": aktif, "algoId": (e or {}).get("algoId")}

    def iz(self, d: dict) -> dict:
        """MADDE 901: iz süren stop koy / değiştir / kaldır. d: sembol, oran (%, boş = kaldır), aktif (isteğe bağlı başlama fiyatı), pin."""
        with self._kilit:
            self._pin(d.get("pin"))
            sem = str(d.get("sembol") or "").upper()
            b = self._sembol_bilgi(sem)
            poz = self._pozisyon(sem)
            if not poz["adet"]:
                raise Hata(f"{sem} için açık pozisyon yok")
            self._gecis_denetle(sem)
            m = None if self.ayar.get("ayri") else self._muhasebe(sem)
            if m and float(m.get("q_bot") or 0):
                raise Hata("Bu coinde botun da payı var; iz süren stop taşımadan sonra (al-sat hesabında) konabilir.", 403)
            ham = d.get("oran")
            oran = None
            if ham not in (None, ""):
                try:
                    oran = float(str(ham).replace(",", "."))
                except ValueError:
                    raise Hata("geri dönüş oranı geçersiz")
                if not IZ_MIN - 1e-9 <= oran <= IZ_MAX + 1e-9:
                    raise Hata(f"geri dönüş oranı %{IZ_MIN:g} ile %{IZ_MAX:g} arasında olmalı")
            aktif = None
            if oran and d.get("aktif") not in (None, ""):
                try:
                    aktif = float(str(d.get("aktif")).replace(",", "."))
                except ValueError:
                    raise Hata("başlama fiyatı geçersiz")
                isr = self._isaret(sem)
                if not aktif > 0 or abs(aktif / isr - 1) > 0.5:
                    raise Hata(f"başlama fiyatı işaret fiyatının ±%50'si içinde olmalı (işaret {isr:g})")
                if (poz["adet"] > 0 and aktif <= isr) or (poz["adet"] < 0 and aktif >= isr):
                    raise Hata("başlama fiyatı long'da şimdiki fiyatın üstünde, short'ta altında olmalı (kâr yönünde)")
            if oran:
                oran = round(oran, 1)   # Binance callbackRate 0,1 adımlı
            self._elle_isaret(sem)
            if oran:
                out = self._iz_kur(sem, poz["adet"], oran, aktif, b)
            else:
                self._panel_tpsl_iptal(sem, iz=True)
                out = None
            self._kaydet({"olay": "iz", "sembol": sem, "oran": oran, "aktif": aktif, "adet": poz["adet"]})
            self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} iz süren stop " + (f"%{oran:g}" + (f" · başlama {aktif:g}" if aktif else "") if oran else "kaldırıldı"))
            return {"iz": out}

    def tpsl(self, d: dict) -> dict:
        with self._kilit:
            self._pin(d.get("pin"))
            sem = str(d.get("sembol") or "").upper()
            b = self._sembol_bilgi(sem)
            poz = self._pozisyon(sem)
            if not poz["adet"]:
                raise Hata(f"{sem} için açık pozisyon yok")
            y = "L" if poz["adet"] > 0 else "S"
            self._gecis_denetle(sem)
            m = None if self.ayar.get("ayri") else self._muhasebe(sem)
            if m and float(m.get("q_bot") or 0):
                raise Hata("Bu coinde botun da payı var; TP / stop taşımadan sonra (al-sat hesabında) konabilir. Şimdilik yalnız kendi payını "
                           "kapatabilirsin.", 403)
            tp, sl = self._tpsl_denetle(y, self._isaret(sem), d.get("tp"), d.get("sl"))
            self._elle_isaret(sem)
            pid = str(d.get("parca") or "").strip() or None
            if pid:   # madde 863: yalnız bu alım parçasının adedi kadar TP / stop
                return self._parca_tpsl_kur(sem, pid, poz, tp, sl, b)
            out = self._tpsl_kur(sem, poz["adet"], tp, sl, b)
            self._kaydet({"olay": "tpsl", "sembol": sem, "tp": tp, "sl": sl, "adet": poz["adet"]})
            self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} TP/SL güncellendi" + (f" · TP {tp:g}" if tp else "")
                        + (f" · SL {sl:g}" if sl else "") + ("" if tp or sl else " (kaldırıldı)"))
            return {"tpsl": out}

    def kapat(self, d: dict) -> dict:
        from exchange_client import adet_yuvarla
        with self._kilit:
            self._pin(d.get("pin"))
            sem = str(d.get("sembol") or "").upper()
            b = self._sembol_bilgi(sem)
            try:
                oran = float(d.get("oran", 1))
            except (TypeError, ValueError):
                raise Hata("oran geçersiz")
            if not 0 < oran <= 1:
                raise Hata("oran 0 ile 1 arasında olmalı")
            poz = self._pozisyon(sem)
            if not poz["adet"]:
                raise Hata(f"{sem} için açık pozisyon yok")
            self._gecis_denetle(sem)
            hedef = poz["adet"] if self.ayar.get("ayri") else self._kullanici_adet(sem)   # madde 851: geçişte botun payına dokunulmaz
            if not hedef:
                raise Hata(f"{sem.replace('USDT', '')} coininde senin payın yok (kalan adet botun)")
            pid = str(d.get("parca") or "").strip() or None   # madde 862: yalnız bu alım parçası
            if pid:
                self._parca_onbellek.pop(sem, None)
                L = next((x for x in (self.parcalar(sem, poz) or []) if x["id"] == pid), None)
                if L is None:
                    raise Hata("bu alım parçası artık açık değil (yenile)", 409)
                pa = min(abs(L["adet"]), abs(poz["adet"]))
                q = round(pa, int(b.get("quantity_precision", 8))) if oran >= 1 else adet_yuvarla(pa * oran, b, piyasa=True, asagi=True)
                if q >= abs(poz["adet"]) - 1e-12:
                    q, oran = abs(poz["adet"]), 1.0      # tek parça kaldıysa tam kapanış (TP/stop da silinir)
                else:
                    oran = min(0.999999, q / abs(poz["adet"]))
            else:
                q = abs(hedef) if oran >= 1 else adet_yuvarla(abs(hedef) * oran, b, piyasa=True, asagi=True)
            if q <= 0:
                raise Hata("bu oran en küçük adımın altında")
            self._elle_isaret(sem)
            ro = (hedef > 0) == (poz["adet"] > 0) and q <= abs(poz["adet"]) + 1e-12
            kw = dict(symbol=sem, side="SELL" if hedef > 0 else "BUY", type="MARKET", quantity=q, newClientOrderId=_cid())
            if ro:
                kw["reduceOnly"] = "true"
            e = self.ic.futures_create_order(**kw)
            if pid and e.get("orderId") is not None:
                self._parca_yaz(e["orderId"], pid)
            self._parca_onbellek.pop(sem, None)
            iptal = 0
            if oran >= 1:
                iptal = self._panel_tpsl_iptal(sem, tum=True) + self._panel_acik_iptal(sem)
            else:      # kalan adede göre TP/SL adedi düzelir: mevcut panel TP/SL'leri aynı fiyatlarla yeniden kurulur
                self._tpsl_yeniden(sem, b)
                try:   # madde 863: satılan parçanın TP/stop'u silinir, adedi değişen parçalarınki düzeltilir
                    self._parca_tpsl_esitle(sem, b)
                except Exception as ex:
                    logger.warning("parça TP/stop eşitlenemedi %s: %s", sem, ex)
            self._kaydet({"olay": "kapat", "sembol": sem, "oran": oran, "adet": q, "orderId": e.get("orderId"), **({"parca": pid} if pid else {})})
            ne = f"alım parçası ({q:g} adet)" if pid else ("TAMAMI" if oran >= 1 else f"%{oran * 100:.0f}")
            self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} {ne} kapatıldı (adet {q:g})")
            return {"kapat": {"orderId": e.get("orderId"), "adet": q, "durum": e.get("status")}, "iptal": iptal}

    def _tpsl_yeniden(self, sem: str, b: dict) -> None:
        f = getattr(self.ic, "futures_get_open_algo_orders", None)
        if f is None:
            return
        r = f(symbol=sem)
        r = r.get("orders", r) if isinstance(r, dict) else r
        tp = sl = None
        izo = next((o for o in r or [] if str(o.get("clientAlgoId") or "").startswith(ONEK) and _algo_parca(o) is None and _iz_mi(o)), None)
        if izo is not None:   # madde 901: adet değişti -> iz süren stop yeni adetle (tepe / dip izi borsada sıfırdan başlar)
            try:
                self._iz_kur(sem, self._pozisyon(sem)["adet"], float(izo.get("callbackRate") or 0), float(izo.get("activatePrice") or 0) or None, b)
            except Exception as e:
                logger.warning("iz süren stop yeniden kurulamadı %s: %s", sem, e)
        for o in r or []:
            if str(o.get("clientAlgoId") or "").startswith(ONEK) and _algo_parca(o) is None and not _iz_mi(o):
                t = str(o.get("orderType") or o.get("type") or "")
                v = float(o.get("triggerPrice") or 0) or None
                if t.startswith("TAKE_PROFIT"):
                    tp = v
                elif t.startswith("STOP"):
                    sl = v
        if tp or sl:
            self._tpsl_kur(sem, self._pozisyon(sem)["adet"], tp, sl, b)

    def _panel_acik_iptal(self, sem: str) -> int:
        n = 0
        for o in self.ic.futures_get_open_orders(symbol=sem) or []:
            if str(o.get("clientOrderId") or "").startswith(ONEK):
                try:
                    self.ic.futures_cancel_order(symbol=sem, orderId=o["orderId"]); n += 1
                except Exception:
                    pass
        return n

    def iptal(self, d: dict) -> dict:
        with self._kilit:
            self._pin(d.get("pin"))
            sem = str(d.get("sembol") or "").upper()
            self._sembol_bilgi(sem)
            if d.get("orderId") not in (None, ""):      # madde 839: tek bekleyen emir (yalnız panelden konan)
                oid = str(d.get("orderId"))
                hedef = [o for o in self.ic.futures_get_open_orders(symbol=sem) or [] if str(o.get("orderId")) == oid]
                if not hedef:
                    raise Hata("bu emir artık açık değil")
                if not str(hedef[0].get("clientOrderId") or "").startswith(ONEK):
                    raise Hata("yalnız panelden konan emirler buradan iptal edilir")
                self.ic.futures_cancel_order(symbol=sem, orderId=hedef[0]["orderId"])
                self._kaydet({"olay": "iptal", "sembol": sem, "orderId": oid, "adet": 1})
                self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} bekleyen emir iptal edildi")
                return {"iptal": 1}
            n = self._panel_acik_iptal(sem) + self._panel_tpsl_iptal(sem)
            self._kaydet({"olay": "iptal", "sembol": sem, "adet": n})
            self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} panel emirleri iptal edildi ({n})")
            return {"iptal": n}

    # ------------------------------------------------------------ MADDE 862: ALIM PARÇALARI
    # Binance tek yönlü modda bir coinde TEK pozisyon tutar (ortalama giriş). Panel, pozisyonu oluşturan her emri ayrı bir "parça"
    # olarak gösterir: kendi giriş fiyatı, adedi, K/Z'si. Pozisyonu azaltan emir hangi parçadan düşer? Panelden "bu parçayı sat"
    # dendiyse o parçadan (defter/alsat_parca.json: kapanış emri -> parça); başka her azaltma (TP, stop, %25 kapat, Binance
    # uygulaması) en eski parçadan (FIFO). Parçaların toplam adedi borsadaki pozisyona eşittir; toplam K/Z Binance'in açık K/Z'sinden
    # farklı olabilir (Binance azaltmada ortalamayı değiştirmez, kâr/zararı ortalamadan gerçekleştirir).
    def _parca_harita(self) -> dict:
        try:
            with open(self.ayar.get("parca") or os.path.join("defter", "alsat_parca.json"), encoding="utf-8") as f:
                d = json.load(f)
            return d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            return {}

    def _parca_yaz(self, order_id, parca_id: str) -> None:
        yol = self.ayar.get("parca") or os.path.join("defter", "alsat_parca.json")
        d = self._parca_harita(); d.setdefault("kapat", {})[str(order_id)] = str(parca_id)
        try:
            os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
            with open(yol + ".tmp", "w", encoding="utf-8") as f:
                json.dump(d, f)
            os.replace(yol + ".tmp", yol)
        except OSError as e:
            logger.warning("parça haritası yazılamadı: %s", e)

    def _emirler(self, sem: str, poz_adet: float, gun: int = 90) -> tuple:
        """Pozisyonu oluşturan dolumlar, emir başına toplanmış (eskiden yeniye) ve pozisyonun açıldığı yer.
        Binance userTrades en çok 7 günlük pencere verir: geriye doğru pencere pencere okunur, geriye yürüyüş sıfıra inince durulur."""
        simdi = int(self.saat() * 1000); H = 7 * 86400 * 1000
        T, bit = {}, simdi
        bulundu = False
        for _ in range(max(1, gun // 7 + 1)):
            bas = bit - H + 1
            r = self.ic.futures_account_trades(symbol=sem, startTime=bas, endTime=bit, limit=1000) or []
            if len(r) >= 1000:      # yoğun pencere: son dolumdan geriye ikinci istek
                r += self.ic.futures_account_trades(symbol=sem, startTime=bas, endTime=int(min(int(x.get("time") or bit) for x in r)) - 1, limit=1000) or []
            for t in r:
                T[(t.get("id"), t.get("orderId"))] = t
            E = self._emir_topla(T.values())
            if self._acilis(E, poz_adet) is not None:
                bulundu = True; break
            bit = bas - 1
        E = self._emir_topla(T.values())
        return E, self._acilis(E, poz_adet) if bulundu else None

    @staticmethod
    def _emir_topla(T) -> list:
        E = {}
        for t in T:
            o = E.setdefault(t.get("orderId"), {"id": str(t.get("orderId")), "t": int(t.get("time") or 0), "q": 0.0, "tut": 0.0, "kom": 0.0})
            q = float(t.get("qty") or 0) * (1 if t.get("side") == "BUY" else -1)
            o["q"] += q; o["tut"] += abs(q) * float(t.get("price") or 0); o["kom"] += float(t.get("commission") or 0)
            o["t"] = min(o["t"], int(t.get("time") or 0))
        L = [dict(o, q=round(o["q"], 10), fiyat=o["tut"] / abs(o["q"]) if o["q"] else 0.0) for o in E.values() if abs(o["q"]) > 1e-12]
        return sorted(L, key=lambda x: (x["t"], x["id"]))

    @staticmethod
    def _acilis(E: list, poz_adet: float):
        """(indeks, o emirden sonra kalan adet): pozisyonun sıfırdan (ya da ters yönden) açıldığı emir; bulunamazsa None."""
        net = float(poz_adet)
        eps = max(1e-9, abs(poz_adet) * 1e-7)
        for i in range(len(E) - 1, -1, -1):
            once = net - E[i]["q"]
            if abs(once) <= eps or (once > 0) != (net > 0):
                return i, net
            net = once
        return None

    # ------------------------------------------------------------ MADDE 863: PARÇA BAŞINA TP / STOP
    # Her parçanın TP / stop'u o parçanın adedi kadar ayrı bir koşullu emirdir (reduceOnly, işaret fiyatı). Tetiklenince oluşan emir
    # o parçadan düşsün diye algoId -> parça kaydı tutulur; emir kapanınca Binance'ten gerçek emir numarası (actualOrderId) alınıp
    # kapanış haritasına yazılır (parcalar() her hesapta önce bunu çözer).
    def _parca_tpsl_kur(self, sem: str, pid: str, poz: dict, tp, sl, b: dict) -> dict:
        self._parca_onbellek.pop(sem, None)
        L = next((x for x in (self.parcalar(sem, poz) or []) if x["id"] == pid), None)
        if L is None:
            raise Hata("bu alım parçası artık açık değil (yenile)", 409)
        self._panel_tpsl_iptal(sem, parca=pid)
        out = self._parca_emir_kur(sem, pid, L["adet"], tp, sl, b)
        self._kaydet({"olay": "tpsl", "sembol": sem, "parca": pid, "tp": tp, "sl": sl, "adet": L["adet"]})
        self._haber(f"🖐 PANEL: {sem.replace('USDT', '')} alım ({abs(L['adet']):g} adet @ {L['fiyat']:g}) TP/stop" + (f" · TP {tp:g}" if tp else "")
                    + (f" · SL {sl:g}" if sl else "") + ("" if tp or sl else " kaldırıldı"))
        return {"tpsl": out, "parca": pid}

    def _parca_emir_kur(self, sem: str, pid: str, adet: float, tp, sl, b: dict) -> list:
        from exchange_client import adet_yuvarla
        q = adet_yuvarla(abs(adet), b, piyasa=True, asagi=True)
        if q <= 0:
            raise Hata("parça adedi en küçük adımın altında")
        out, d = [], self._parca_harita()
        for ad, tur, v in (("TP", "TAKE_PROFIT_MARKET", tp), ("SL", "STOP_MARKET", sl)):
            if v is None:
                continue
            e = self.ic.futures_create_algo_order(algoType="CONDITIONAL", symbol=sem, side="SELL" if adet > 0 else "BUY", type=tur,
                                                  triggerPrice=self._fiyat_yuvarla(v, b), quantity=q, reduceOnly="true",
                                                  workingType="MARK_PRICE", clientAlgoId=_parca_cid(pid, ad[0]))
            aid = (e or {}).get("algoId")
            if aid is not None:
                d.setdefault("algo", {})[str(aid)] = {"p": pid, "s": sem}
            out.append({"tur": ad, "fiyat": v, "algoId": aid})
        self._parca_harita_yaz(d)
        return out

    def _parca_harita_yaz(self, d: dict) -> None:
        yol = self.ayar.get("parca") or os.path.join("defter", "alsat_parca.json")
        try:
            os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
            with open(yol + ".tmp", "w", encoding="utf-8") as f:
                json.dump(d, f)
            os.replace(yol + ".tmp", yol)
        except OSError as e:
            logger.warning("parça haritası yazılamadı: %s", e)

    def _parca_algo_coz(self, sem: str, acik: list | None = None) -> None:
        """Artık açık olmayan parça TP/stop'ları: tetiklendiyse gerçek emir numarasını kapanış haritasına yaz, kaydı sil."""
        d = self._parca_harita(); A = d.get("algo") or {}
        bekleyen = {k: v for k, v in A.items() if v.get("s") == sem}
        if not bekleyen:
            return
        acik_id = {str(o.get("algoId")) for o in (acik if acik is not None else self._acik_algolar(sem))}
        degisti = False
        for aid, v in bekleyen.items():
            if aid in acik_id:
                continue
            oid = None
            try:
                g = getattr(self.ic, "futures_get_algo_order", None)
                x = g(algoId=int(aid)) if g else {}
                oid = (x or {}).get("actualOrderId") or None
                durum = str((x or {}).get("algoStatus") or "")
                if not oid and durum in ("NEW", "TRIGGERING"):
                    continue
            except Exception as e:
                logger.info("parça algo sorgulanamadı %s: %s", aid, str(e)[:120])
                continue
            if oid and str(oid) not in ("0", "-1"):
                d.setdefault("kapat", {})[str(oid)] = v["p"]
            A.pop(aid, None); degisti = True
        if degisti:
            d["algo"] = A
            self._parca_harita_yaz(d)
            self._parca_onbellek.pop(sem, None)

    def _parca_tpsl(self, sem: str, acik: list | None = None) -> dict:
        """{parça: {"tp": fiyat, "sl": fiyat, "q": adet}} — açık parça TP/stop emirleri."""
        P = {}
        for o in (acik if acik is not None else self._acik_algolar(sem)):
            p = _algo_parca(o)
            if p is None:
                continue
            t = str(o.get("orderType") or o.get("type") or "")
            k = P.setdefault(p, {})
            k["tp" if t.startswith("TAKE_PROFIT") else "sl"] = float(o.get("triggerPrice") or 0) or None
            k["q"] = float(o.get("quantity") or o.get("origQty") or 0) or k.get("q")
        return P

    def _parca_tpsl_esitle(self, sem: str, b: dict | None = None) -> int:
        """Satılmış parçanın TP/stop'unu siler; adedi küçülen parçanınkini yeni adetle yeniden kurar. Yapılan değişiklik sayısı."""
        from exchange_client import adet_yuvarla
        acik = self._acik_algolar(sem)
        T = self._parca_tpsl(sem, acik)
        if not T:
            return 0
        self._parca_onbellek.pop(sem, None)
        L = {x["id"]: x for x in (self.parcalar(sem) or [])}
        b = b or self._sembol_bilgi(sem)
        n = 0
        for pid, k in T.items():
            x = L.get(pid)
            if x is None:
                n += self._panel_tpsl_iptal(sem, parca=pid)
                continue
            q = adet_yuvarla(abs(x["adet"]), b, piyasa=True, asagi=True)
            if k.get("q") and abs(k["q"] - q) > 1e-9:
                self._panel_tpsl_iptal(sem, parca=pid)
                self._parca_emir_kur(sem, pid, x["adet"], k.get("tp"), k.get("sl"), b); n += 1
        return n

    def parcalar(self, sem: str, poz: dict | None = None) -> list | None:
        """Açık pozisyonun parçaları (eskiden yeniye): {id, t, adet (işaretli), fiyat, kom}. Ayrı hesap yoksa None."""
        if not self.ayar.get("ayri"):
            return None
        poz = poz or self._pozisyon(sem)
        A = float(poz.get("adet") or 0)
        if not A:
            return []
        k = self._parca_onbellek.get(sem)
        if k and k[0] == A and self.saat() - k[1] < 60:
            return k[2]
        try:
            self._parca_algo_coz(sem)
        except Exception as e:
            logger.info("parça TP/stop çözülemedi %s: %s", sem, str(e)[:120])
        E, ac = self._emirler(sem, A)
        self._acilis_t[sem] = E[ac[0]]["t"] if ac is not None else None   # madde 902: pozisyonun açıldığı an
        harita = self._parca_harita().get("kapat", {})
        lots = []
        if ac is None:      # 90 günden eski: tek parça, borsa ortalamasıyla
            lots = [{"id": "eski", "t": 0, "adet": A, "fiyat": float(poz.get("giris") or 0), "kom": 0.0, "eski": True}]
        else:
            i, ilk = ac; o = E[i]
            lots = [{"id": o["id"], "t": o["t"], "adet": round(ilk, 10), "fiyat": o["fiyat"], "kom": o["kom"] * abs(ilk / o["q"])}]
            for o in E[i + 1:]:
                q = o["q"]
                hedef = harita.get(o["id"])
                while abs(q) > 1e-12 and lots and (lots[0]["adet"] > 0) != (q > 0):
                    L = next((x for x in lots if x["id"] == hedef), None) or lots[0]
                    al = min(abs(q), abs(L["adet"]))
                    L["adet"] = round(L["adet"] - al * (1 if L["adet"] > 0 else -1), 10)
                    q = round(q - al * (1 if q > 0 else -1), 10)
                    if abs(L["adet"]) <= max(1e-12, abs(A) * 1e-9):
                        lots.remove(L)
                if abs(q) > 1e-12:
                    lots.append({"id": o["id"], "t": o["t"], "adet": q, "fiyat": o["fiyat"], "kom": o["kom"] * abs(q / o["q"])})
            fark = round(A - sum(x["adet"] for x in lots), 10)
            if abs(fark) > max(1e-9, abs(A) * 1e-6):   # okunamayan dolum: farkı borsa ortalamasıyla ayrı parça yap
                logger.warning("parça toplamı pozisyonla uyuşmuyor %s: fark %s", sem, fark)
                if (fark > 0) == (A > 0):
                    lots.append({"id": "fark", "t": 0, "adet": fark, "fiyat": float(poz.get("giris") or 0), "kom": 0.0, "eski": True})
        for x in lots:
            x["kom"] = round(x["kom"], 6)
        self._parca_onbellek[sem] = (A, self.saat(), lots)
        return lots

    def pozisyon(self, sem: str) -> dict:
        sem = str(sem or "").upper()
        self._sembol_bilgi(sem)
        poz = self._pozisyon(sem)
        bot_pay = 0.0
        if not self.ayar.get("ayri") and poz["adet"]:   # madde 851: geçişte pencere yalnız KULLANICININ payını gösterir
            m = self._muhasebe(sem)
            if m and m.get("q_k") is not None:
                qk, ok_ = float(m["q_k"]), float(m.get("ort_k") or 0)
                isr = poz["giris"] + poz["kz"] / poz["adet"]
                bot_pay = float(m.get("q_bot") or 0)
                poz = {"adet": qk, "giris": ok_, "kz": round(qk * (isr - ok_), 4) if qk and ok_ else 0.0, "likidasyon": poz["likidasyon"],
                       "borsa": dict(poz)}
        tpsl, bekleyen = [], []
        try:
            f = getattr(self.ic, "futures_get_open_algo_orders", None)
            r = f(symbol=sem) if f else []
            r = r.get("orders", r) if isinstance(r, dict) else r
            for o in r or []:
                if _algo_parca(o) is not None:
                    continue      # madde 863: parçanın kendi TP/stop'u parça satırında
                t = str(o.get("orderType") or o.get("type") or "")
                if _iz_mi(o):   # madde 901
                    tpsl.append({"tur": "IZ", "oran": float(o.get("callbackRate") or 0), "aktif": float(o.get("activatePrice") or 0) or None,
                                 "fiyat": float(o.get("activatePrice") or 0), "panel": str(o.get("clientAlgoId") or "").startswith(ONEK)})
                    continue
                tpsl.append({"tur": "TP" if t.startswith("TAKE_PROFIT") else "SL" if t.startswith("STOP") else t,
                             "fiyat": float(o.get("triggerPrice") or 0), "panel": str(o.get("clientAlgoId") or "").startswith(ONEK)})
            for o in self.ic.futures_get_open_orders(symbol=sem) or []:
                bekleyen.append({"orderId": o.get("orderId"), "tip": o.get("type"), "yon": o.get("side"), "fiyat": float(o.get("price") or 0),
                                 "adet": float(o.get("origQty") or 0), "panel": str(o.get("clientOrderId") or "").startswith(ONEK)})
        except Exception as e:
            logger.warning("pozisyon emirleri okunamadı %s: %s", sem, e)
        islemler = []   # madde 835: grafikte giriş / çıkış işaretleri (son 7 gün, en çok 100 dolum; hesabın kendi işlemleri)
        try:
            for t in self.ic.futures_account_trades(symbol=sem, startTime=int((self.saat() - 7 * 86400) * 1000), limit=100) or []:
                islemler.append({"t": int(t.get("time") or 0), "yon": "AL" if t.get("side") == "BUY" else "SAT",
                                 "fiyat": float(t.get("price") or 0), "adet": float(t.get("qty") or 0),
                                 "kz": float(t.get("realizedPnl") or 0)})
        except Exception as e:
            logger.warning("işlem geçmişi okunamadı %s: %s", sem, e)
        parca = None
        try:
            parca = self.parcalar(sem, poz) if poz.get("adet") else []
            if parca and self.ayar.get("ayri"):
                if self._kilit.acquire(blocking=False):   # adedi değişmiş parça TP/stop'larını düzelt (işlem sürüyorsa atla)
                    try:
                        if self._parca_tpsl_esitle(sem):
                            parca = self.parcalar(sem, poz)
                    finally:
                        self._kilit.release()
                T = self._parca_tpsl(sem)
                parca = [{**x, "tp": T.get(x["id"], {}).get("tp"), "sl": T.get(x["id"], {}).get("sl")} for x in parca]
        except Exception as e:
            logger.warning("parçalar okunamadı %s: %s", sem, e)
        gelir = None
        if self.ayar.get("ayri") and poz.get("adet"):   # madde 902
            try:
                gelir = self._poz_gelirleri({sem: self._acilis_t.get(sem)}).get(sem)
            except Exception as e:
                logger.info("pozisyon gelirleri okunamadı %s: %s", sem, str(e)[:120])
        return {"sembol": sem, "pozisyon": poz, "isaret": self._isaret(sem), "tpsl": tpsl, "bekleyen": bekleyen, "mod": self.ayar["mod"], "parcalar": parca, "gelir": gelir,
                "islemler": islemler, "elle": bool(self.ayar.get("ayri")) or sem in self._elle_kumesi(),
                "bot_tutuyor": False if self.ayar.get("ayri") else self._bot_tutuyor(sem), "bot_pay": bot_pay}

    # ------------------------------------------------------------ madde 839: elle özeti
    def _elle_kumesi(self) -> set:
        try:
            import carry_elle
            return carry_elle.isaretliler(self.ayar.get("elle_dosya") or "carry_elle.json") | carry_elle.panel_isaretleri(
                self.ayar.get("elle_panel"), self.ayar.get("elle_dosya"), int(self.saat() * 1000))
        except Exception:
            return set()

    def _bot_tutuyor(self, sem: str) -> bool:
        try:
            with open(self.ayar.get("dilim") or "carry_dilimler.json", encoding="utf-8") as f:
                d = json.load(f)
            return any(sem in (h or {}) for h in (d.get("dilimler") or {}).values())
        except (OSError, ValueError, AttributeError):
            return False

    def _elle_araliklar(self, gun: int = 30) -> dict:
        """{sembol: [(baş_ms, bit_ms), ...]} — kullanıcının coine sahip olduğu aralıklar (olay defteri + panel işaretleri), son `gun` gün."""
        simdi = int(self.saat() * 1000); alt = simdi - gun * 86400 * 1000
        acik, A = {}, {}
        try:
            with open(self.ayar.get("elle_olay") or "carry_elle_olay.jsonl", encoding="utf-8") as f:
                for satir in f:
                    try:
                        o = json.loads(satir)
                    except ValueError:
                        continue
                    sem, t = o.get("sembol"), int(o.get("t") or 0)
                    if o.get("olay") == "isaret":
                        acik.setdefault(sem, t)
                    elif o.get("olay") == "birak" and sem in acik:
                        A.setdefault(sem, []).append((acik.pop(sem), t))
        except OSError:
            pass
        try:
            import carry_elle
            for sem, t in carry_elle.panel_okuma(self.ayar.get("elle_panel")).items():
                if sem not in acik and not any(a <= t <= b for a, b in A.get(sem, [])):
                    acik[sem] = min(t, acik.get(sem, t))
        except Exception:
            pass
        for sem, t in acik.items():
            A.setdefault(sem, []).append((t - 60_000, simdi + 60_000))   # açık aralık: saat kayması payı
        return {s: [(max(a, alt), b) for a, b in L if b >= alt] for s, L in A.items() if any(b >= alt for a, b in L)}

    def _muhasebe(self, sem: str) -> dict | None:
        """MADDE 850: carry_elle_kz kaydındaki AÇIK elle aralık (botun muhasebesiyle aynı kaynak) ya da None."""
        try:
            import carry_elle_kz
            L = (carry_elle_kz._oku(self.ayar.get("elle_kz") or carry_elle_kz.DOSYA).get("aralik") or {}).get(sem) or []
            A = [a for a in L if not a.get("bit") and a.get("kz") is not None]
            return A[-1] if A else None
        except Exception:
            return None

    def _payim(self, sem: str, adet: float, giris: float) -> dict | None:
        """MADDE 843: elle pozisyonun KULLANICIYA ait kısmı. Sahiplik başından (panel işareti ya da işaret olayı, hangisi önceyse) bu yana
        hesabın dolumları kullanıcınındır (bot elle coine emir göndermez). Emir başına ortalama dolum fiyatı; kalan adet bottan devralınandır.
        Devralınanın girişi borsa ortalamasından geri çözülür: yalnız bütün dolumlar pozisyonu BÜYÜTTÜYSE (azaltma ortalamayı değiştirmez ama
        hangi parçadan düştüğü bilinmez -> o zaman verilmez)."""
        L = self._elle_araliklar().get(sem) or []
        simdi = int(self.saat() * 1000)
        acik = [a for a, b in L if b >= simdi]
        if not acik:
            return None
        bas = min(acik)
        try:
            import carry_elle
            pt = carry_elle.panel_okuma(self.ayar.get("elle_panel")).get(sem)
            if pt and pt - 60_000 < bas and not any(a <= pt <= b for a, b in L if b < simdi):
                bas = pt - 60_000
        except Exception:
            pass
        m = self._muhasebe(sem)   # madde 850: muhasebe (carry_elle_kz) ilk kullanıcı dolumunu bilir — saatlik işaret ondan geç olabilir
        if m and m.get("bas") and int(m["bas"]) - 1000 < bas:
            bas = int(m["bas"]) - 1000
        try:
            T = self.ic.futures_account_trades(symbol=sem, startTime=int(bas), limit=500) or []
        except Exception as e:
            logger.warning("elle payı okunamadı %s: %s", sem, e)
            return None
        E = {}
        for t in T:
            o = E.setdefault(t.get("orderId"), {"t": int(t.get("time") or 0), "yon": "AL" if t.get("side") == "BUY" else "SAT", "adet": 0.0, "tut": 0.0})
            q = float(t.get("qty") or 0); o["adet"] += q; o["tut"] += q * float(t.get("price") or 0); o["t"] = min(o["t"], int(t.get("time") or 0))
        dolum = sorted(({"t": o["t"], "yon": o["yon"], "adet": round(o["adet"], 10), "fiyat": o["tut"] / o["adet"]} for o in E.values() if o["adet"] > 0),
                       key=lambda x: x["t"])
        isaret = 1 if adet > 0 else -1
        net = sum(x["adet"] * (1 if x["yon"] == "AL" else -1) for x in dolum)
        devr = round(adet - net, 10)
        buyuten = [x for x in dolum if (x["yon"] == "AL") == (adet > 0)]
        benim_giris = (sum(x["adet"] * x["fiyat"] for x in buyuten) / sum(x["adet"] for x in buyuten)) if buyuten else None
        devr_giris = None
        if devr * isaret > 1e-12 and len(buyuten) == len(dolum) and giris > 0:
            g = (giris * abs(adet) - sum(x["adet"] * x["fiyat"] for x in dolum)) / abs(devr)
            devr_giris = g if g > 0 else None
        return {"bas": int(bas + 60_000), "dolum": dolum[-20:], "benim_adet": round(net, 10), "benim_giris": benim_giris,
                "devralinan": devr if abs(devr) > 1e-12 else 0.0, "devralinan_giris": devr_giris}

    def _poz_gelirleri(self, acilis: dict) -> dict:
        """MADDE 902: açık pozisyon başına, açıldığı andan bu yana gelir kayıtları: funding, komisyon, gerçekleşen (kısmi kapanışlar).
        Tek gelir sorgusu (en eski açılıştan, en çok 90 gün), 120 sn önbellek. {sembol: {fon, kom, gercek, t}}"""
        A = {s: t for s, t in acilis.items() if t}
        if not A:
            return {}
        simdi = int(self.saat() * 1000)
        bas = max(min(A.values()), simdi - 90 * 86400 * 1000)
        o = self._poz_gelir_onb
        if o and o[0] <= bas and self.saat() - o[1] < 120:
            G = o[2]
        else:
            G = _gelirler(self.ic, bas, simdi)
            self._poz_gelir_onb = (bas, self.saat(), G)
        out = {s: {"fon": 0.0, "kom": 0.0, "gercek": 0.0, "t": t} for s, t in A.items()}
        for g in G:
            s, t = g.get("symbol"), int(g.get("time") or 0)
            if s not in out or t < A[s]:
                continue
            k = {"FUNDING_FEE": "fon", "COMMISSION": "kom", "REALIZED_PNL": "gercek"}.get(str(g.get("incomeType") or ""))
            if k:
                out[s][k] += float(g.get("income") or 0)
        return {s: {k: (round(v, 4) if k != "t" else v) for k, v in d.items()} for s, d in out.items()}

    def elle_ozet(self) -> dict:
        """Elle pozisyonların (açık) ve son 30 gün elle sonucunun (gerçekleşen K/Z + komisyon, yalnız elle aralıklarındaki dolumlar)."""
        ayri = bool(self.ayar.get("ayri"))   # madde 851: ayrı hesapta bütün pozisyonlar kullanıcının
        elle = set() if ayri else self._elle_kumesi()
        pozlar = []
        tum_algo = None   # madde 856: bütün açık TP/stop emirleri TEK sorguda (coin başına sorgu 15 pozisyonda ~5 sn sürüyordu)
        try:
            f = getattr(self.ic, "futures_get_open_algo_orders", None)
            if f:
                r = f()
                r = r.get("orders", r) if isinstance(r, dict) else r
                tum_algo = {}
                for o in r or []:
                    tum_algo.setdefault(o.get("symbol"), []).append(o)
        except Exception as e:
            logger.info("toplu TP/stop okunamadı (%s) — coin başına", str(e)[:120])
            tum_algo = None
        for p in self.c.get_open_positions():
            sem = p.get("symbol")
            a = float(p.get("positionAmt") or 0)
            if (ayri or sem in elle) and a:
                tp = sl = iz = None
                p_tp, p_sl = set(), set()
                try:
                    if tum_algo is not None:
                        r = tum_algo.get(sem, [])
                    else:
                        f = getattr(self.ic, "futures_get_open_algo_orders", None)
                        r = f(symbol=sem) if f else []
                        r = r.get("orders", r) if isinstance(r, dict) else r
                    for o in r or []:
                        t = str(o.get("orderType") or o.get("type") or "")
                        if _algo_parca(o) is not None:   # madde 863: parça TP/stop'u
                            (p_tp if t.startswith("TAKE_PROFIT") else p_sl).add(_algo_parca(o))
                            continue
                        if t.startswith("TAKE_PROFIT"):
                            tp = float(o.get("triggerPrice") or 0) or None
                        elif t.startswith("STOP"):
                            sl = float(o.get("triggerPrice") or 0) or None
                        elif _iz_mi(o):   # madde 901
                            iz = float(o.get("callbackRate") or 0) or None
                except Exception:
                    pass
                parca = None
                if ayri:
                    try:
                        parca = self.parcalar(sem, {"adet": a, "giris": float(p.get("entryPrice") or 0)})
                    except Exception as e:
                        logger.info("parçalar okunamadı %s: %s", sem, str(e)[:120])
                pozlar.append({"sembol": sem, "adet": a, "giris": float(p.get("entryPrice") or 0), "parcalar": parca,
                               "parca_tp": len(p_tp), "parca_sl": len(p_sl),
                               "kz": float(p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0),
                               "likidasyon": float(p.get("liquidationPrice") or 0), "tp": tp, "sl": sl, "iz": iz,
                               "pay": None if ayri else self._payim(sem, a, float(p.get("entryPrice") or 0))})   # madde 843
                m = self._muhasebe(sem)
                if m and not self.ayar.get("ayri") and m.get("q_k") is not None:   # madde 851: geçişte yalnız kullanıcının payı
                    P_ = pozlar[-1]; isr = P_["giris"] + P_["kz"] / P_["adet"] if P_["adet"] else 0
                    qk, ok_ = float(m["q_k"]), float(m.get("ort_k") or 0)
                    if not qk:
                        pozlar.pop(); continue
                    uk = qk * (isr - ok_) if ok_ and isr else 0.0
                    P_["borsa"] = {"adet": P_["adet"], "giris": P_["giris"], "kz": P_["kz"]}
                    P_.update(adet=qk, giris=ok_, kz=round(uk, 4), pay=None)
                    P_["muhasebe"] = {"kz": round(float(m.get("Rk") or 0) + float(m.get("Fk") or 0) + float(m.get("C") or 0) + uk, 4),
                                      "q_bot": float(m.get("q_bot") or 0), "e_bot": m.get("e_bot"), "funding": round(float(m.get("Fk") or 0), 4),
                                      "komisyon": round(float(m.get("C") or 0), 4), "bas": int(m.get("bas") or 0), "kural": "bota_geri"}
                elif m:
                    u = pozlar[-1]["kz"]
                    pozlar[-1]["muhasebe"] = {"kz": round(float(m["kz"]) + u - float(m.get("U") or 0), 4), "devir": round(float(m.get("devir") or 0), 4),
                                              "devr_adet": float(m.get("devr_adet") or 0), "ilk_fiyat": float(m.get("ilk_fiyat") or 0),
                                              "funding": round(float(m.get("F") or 0), 4), "komisyon": round(float(m.get("C") or 0), 4),
                                              "bas": int(m.get("bas") or 0)}
        if ayri:   # madde 902: pozisyonun kendi funding / komisyon / kısmi kapanış toplamı (açıldığından beri)
            try:
                PG = self._poz_gelirleri({x["sembol"]: self._acilis_t.get(x["sembol"]) for x in pozlar})
                for x in pozlar:
                    if x["sembol"] in PG:
                        x["gelir"] = PG[x["sembol"]]
            except Exception as e:
                logger.info("pozisyon gelirleri okunamadı: %s", str(e)[:120])
        kz = kom = 0.0; kapanis = kazanan = 0
        if ayri:   # ayrı hesap: son 30 günün bütün gelir kayıtları
            hesap = {}
            try:   # madde 860: toplam bakiye + pozisyonlara bağlı teminat + boşta (kullanılabilir) bakiye
                h = _hesap_ozet(self.ic, ayrinti=True)
                hesap = {k: round(v, 2) for k, v in h.items()}
                hesap["buyukluk"] = round(sum(abs(x["adet"]) * (x["giris"] + (x["kz"] / x["adet"] if x["adet"] else 0)) for x in pozlar), 2)
            except Exception as e:
                logger.warning("al-sat hesap özkaynağı okunamadı: %s", e)
            try:
                bas = int((self.saat() - 30 * 86400) * 1000)
                for x in self.ic.futures_income_history(startTime=bas, limit=1000) or []:
                    t, v = x.get("incomeType"), float(x.get("income") or 0)
                    if t == "REALIZED_PNL":
                        kz += v; kapanis += 1; kazanan += v > 0
                    elif t == "COMMISSION":
                        kom -= v
                    elif t == "FUNDING_FEE":
                        kz += v
            except Exception as e:
                logger.warning("al-sat sonucu okunamadı: %s", e)
            pozlar.sort(key=lambda x: x["kz"])
            return {"pozisyonlar": pozlar, "sonuc": {"gun": 30, "kz": round(kz, 4), "komisyon": round(kom, 4), "net": round(kz - kom, 4),
                                                      "kapanis": kapanis, "kazanan": kazanan}, "mod": self.ayar["mod"], "hesap": hesap, "ayri": True,
                    "onceki": onceki_elle(self)}
        for sem, L in list(self._elle_araliklar().items())[:25]:
            try:
                for t in self.ic.futures_account_trades(symbol=sem, startTime=min(a for a, _ in L), limit=500) or []:
                    zt = int(t.get("time") or 0)
                    if not any(a <= zt <= b for a, b in L):
                        continue
                    r = float(t.get("realizedPnl") or 0)
                    kz += r; kom += float(t.get("commission") or 0)
                    if r:
                        kapanis += 1; kazanan += r > 0
            except Exception as e:
                logger.warning("elle sonucu okunamadı %s: %s", sem, e)
        pozlar.sort(key=lambda x: x["kz"])
        return {"pozisyonlar": pozlar, "sonuc": {"gun": 30, "kz": round(kz, 4), "komisyon": round(kom, 4), "net": round(kz - kom, 4),
                                                  "kapanis": kapanis, "kazanan": kazanan}, "mod": self.ayar["mod"]}


# ------------------------------------------------------------------ madde 852: AL-SAT GEÇMİŞİ (ayrı hesap)
TR_SAAT = 0                 # madde 860: gün sınırı 00:00 UTC = gece 03:00 TR (Binance günü; botla aynı). Eskiden 00:00 TR idi.
ANLIK_ARA_SN = 300


def _gun(ms: int) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(ms / 1000 + TR_SAAT))


def _hesap_ozet(ic, ayrinti: bool = False) -> dict:
    h = ic.futures_account()
    out = {"ozkaynak": float(h.get("totalMarginBalance") or 0), "cuzdan": float(h.get("totalWalletBalance") or 0),
           "acik": float(h.get("totalUnrealizedProfit") or 0)}
    if ayrinti:   # madde 860: pozisyon teminatı, açık emir teminatı, boşta (yeni işlemde kullanılabilir) bakiye
        out.update(teminat=float(h.get("totalPositionInitialMargin") or 0), emir_teminat=float(h.get("totalOpenOrderInitialMargin") or 0),
                   bosta=float(h.get("availableBalance") or 0))
    return out


def anlik_kaydet(kapi: "Kapi", simdi: float | None = None) -> dict | None:
    """MADDE 852: al-sat hesabının özkaynak noktası → defter/alsat_anlik.jsonl (5 dk'da bir; yalnız ayrı hesapta)."""
    if not kapi.ayar.get("ayri"):
        return None
    h = _hesap_ozet(kapi.ic)
    nokta = {"t": int((simdi or kapi.saat()) * 1000), **{k: round(v, 4) for k, v in h.items()}}
    yol = kapi.ayar.get("anlik") or os.path.join("defter", "alsat_anlik.jsonl")
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    with open(yol, "a", encoding="utf-8") as f:
        f.write(json.dumps(nokta) + "\n")
    try:   # 60 günden eskiler atılır
        if os.path.getsize(yol) > 3_000_000:
            alt = nokta["t"] - 60 * 86400 * 1000
            L = [l for l in open(yol, encoding="utf-8") if l.strip() and json.loads(l).get("t", 0) >= alt]
            with open(yol + ".tmp", "w", encoding="utf-8") as f:
                f.writelines(L)
            os.replace(yol + ".tmp", yol)
    except (OSError, ValueError):
        pass
    return nokta


def _gelirler(ic, bas_ms: int, bit_ms: int) -> list:
    out, s = [], int(bas_ms)
    for _ in range(200):
        r = ic.futures_income_history(startTime=s, endTime=bit_ms, limit=1000) or []
        out += r
        if len(r) < 1000:
            break
        s = int(r[-1].get("time") or s) + 1
    return out


def onceki_elle(kapi: "Kapi") -> dict | None:
    """MADDE 854: taşımadan (madde 851) önce bot hesabında kesinleşen elle K/Z — dondurulmuş carry_elle_kz kaydı. Yoksa None."""
    try:
        import carry_elle_kz
        st = carry_elle_kz._oku(kapi.ayar.get("elle_kz") or carry_elle_kz.DOSYA)
    except Exception:
        return None
    if not st.get("donduruldu"):
        return None
    S = {}
    for s, L in (st.get("aralik") or {}).items():
        v = sum(float(a.get("kz") or 0) for a in L)
        if abs(v) >= 0.005:
            S[s] = round(v, 2)
    return {"toplam": round(float(st.get("toplam") or 0), 2), "sembol": S, "t": int(st["donduruldu"])}


def _kapanislar(islem: list, en_cok: int = 200) -> list:
    """MADDE 895: kapanan işlemler — REALIZED_PNL kayıtları coin başına 60 sn içinde birleştirilir (bir emrin parça dolumları tek
    kapanış); net = gerçekleşen + aynı işlemlerin (tradeId) komisyonu. Yeniden eskiye."""
    kom = {}
    for g in islem:
        if str(g.get("incomeType")) == "COMMISSION" and g.get("tradeId") not in (None, ""):
            k = (g.get("symbol"), str(g.get("tradeId")))
            kom[k] = kom.get(k, 0.0) + float(g.get("income") or 0)
    R = sorted((g for g in islem if str(g.get("incomeType")) == "REALIZED_PNL" and g.get("symbol")), key=lambda g: int(g.get("time") or 0))
    son, out = {}, []
    for g in R:
        t, s_ = int(g.get("time") or 0), g["symbol"]
        x = son.get(s_)
        if not x or t - x["_son"] > 60000:
            x = {"t": t, "s": s_.removesuffix("USDT"), "kz": 0.0, "kom": 0.0, "n": 0, "_son": t}
            son[s_] = x; out.append(x)
        x["kz"] += float(g.get("income") or 0); x["n"] += 1; x["_son"] = t
        x["kom"] += kom.pop((s_, str(g.get("tradeId"))), 0.0)
    return [{"t": x["t"], "s": x["s"], "kz": round(x["kz"], 4), "net": round(x["kz"] + x["kom"], 4), "n": x["n"]} for x in reversed(out)][:en_cok]


def gecmis(kapi: "Kapi", gun: int = 90) -> dict:
    """MADDE 852: al-sat hesabının günlük kazanç / kayıp ve hesap eğrisi.
    Başlangıç sermayesi = cüzdan − bütün işlem gelirleri (gerçekleşen + funding + komisyon; transfer hariç).
    Gün sonu özkaynağı: o günün son anlık noktası; nokta yoksa başlangıç + o güne kadarki gelirler (açık K/Z bilinmez)."""
    if not kapi.ayar.get("ayri"):
        raise Hata("al-sat ayrı hesabı bağlı değil", 409)
    simdi = int(kapi.saat() * 1000)
    h = _hesap_ozet(kapi.ic)
    G = [g for g in _gelirler(kapi.ic, simdi - gun * 86400 * 1000, simdi) if str(g.get("asset") or "USDT") == "USDT"]
    tur = lambda g: str(g.get("incomeType") or "")
    islem = [g for g in G if tur(g) != "TRANSFER"]
    top = {"gerceklesen": 0.0, "funding": 0.0, "komisyon": 0.0, "diger": 0.0}
    gunluk, coin = {}, {}
    for g in islem:
        v = float(g.get("income") or 0); t = tur(g)
        k = "gerceklesen" if t == "REALIZED_PNL" else "funding" if t == "FUNDING_FEE" else "komisyon" if t == "COMMISSION" else "diger"
        top[k] += v
        if g.get("symbol"):   # madde 855: coin bazında (bottaki Geçmiş tablosu gibi)
            cc = coin.setdefault(g["symbol"], {"kapanan": 0.0, "funding": 0.0, "komisyon": 0.0})
            cc["kapanan" if k == "gerceklesen" else k if k in ("funding", "komisyon") else "kapanan"] += v
        d = gunluk.setdefault(_gun(int(g.get("time") or 0)), {"gerceklesen": 0.0, "funding": 0.0, "komisyon": 0.0, "diger": 0.0})
        d[k] += v
    bas = h["cuzdan"] - sum(top.values())
    N = []
    try:
        with open(kapi.ayar.get("anlik") or os.path.join("defter", "alsat_anlik.jsonl"), encoding="utf-8") as f:
            for l in f:
                try:
                    x = json.loads(l)
                    N.append((int(x["t"]), float(x["ozkaynak"])))
                except (ValueError, KeyError, TypeError):
                    continue
    except OSError:
        pass
    N.sort()
    son_nokta = {}
    for t, v in N:
        son_nokta[_gun(t)] = v
    ilk = min([int(g.get("time") or simdi) for g in islem] + [t for t, _ in N] + [simdi])
    gunler, onceki, birikim = [], bas, 0.0
    d0 = time.strftime("%Y-%m-%d", time.gmtime(ilk / 1000 + TR_SAAT))
    bugun = _gun(simdi)
    import calendar
    t = calendar.timegm(time.strptime(d0, "%Y-%m-%d"))
    while True:
        g = time.strftime("%Y-%m-%d", time.gmtime(t))
        if g > bugun:
            break
        b = gunluk.get(g, {"gerceklesen": 0.0, "funding": 0.0, "komisyon": 0.0, "diger": 0.0})
        birikim += sum(b.values())
        son = h["ozkaynak"] if g == bugun else son_nokta.get(g, bas + birikim)
        gunler.append({"t": g, "kz": round(son - onceki, 4), "oz": round(son, 4), **{k: round(v, 4) for k, v in b.items()}})
        onceki = son
        t += 86400
    egri, son_saat = [[ilk - 1, round(bas, 4)]], None
    for t_, v in N:                       # saatte bir nokta
        s_ = t_ // 3600000
        if s_ != son_saat:
            egri.append([t_, round(v, 4)]); son_saat = s_
        else:
            egri[-1] = [t_, round(v, 4)]
    egri.append([simdi, round(h["ozkaynak"], 4)])
    toplam = h["ozkaynak"] - bas
    acik_poz = {}
    try:
        for p in kapi.c.get_open_positions():
            a_ = float(p.get("positionAmt") or 0)
            if a_:
                acik_poz[p["symbol"]] = (a_, float(p.get("unRealizedProfit") or p.get("unrealizedProfit") or 0))
    except Exception as e:
        logger.warning("al-sat pozisyonları okunamadı: %s", e)
    coin_ozet = []
    for s in set(coin) | set(acik_poz):
        cc = coin.get(s, {"kapanan": 0.0, "funding": 0.0, "komisyon": 0.0}); a_, u = acik_poz.get(s, (0.0, 0.0))
        coin_ozet.append({"s": s.removesuffix("USDT"), **{k: round(v, 4) for k, v in cc.items()}, "acik": round(u, 4),
                          "toplam": round(sum(cc.values()) + u, 4), "yon": ("L" if a_ > 0 else "S") if a_ else None})
    coin_ozet.sort(key=lambda x: x["toplam"])
    return {"onceki": onceki_elle(kapi), "coin_ozet": coin_ozet, "kapanislar": _kapanislar(islem),
            "baslangic": round(bas, 2), "ozkaynak": round(h["ozkaynak"], 2), "acik": round(h["acik"], 2), "toplam": round(toplam, 2),
            "oran": round(toplam / bas, 6) if bas > 0 else None, "ozet": {k: round(v, 2) for k, v in top.items()},
            "gunler": gunler[-gun:], "egri": egri}


def uygulama(kapi_fabrika=None):
    """Flask uygulaması. `kapi_fabrika` testte sahte borsalı Kapi verir; yoksa gerçek anahtarla (config) ilk istekte kurulur."""
    from flask import Flask, jsonify, request
    app = Flask(__name__)
    durum = {"kapi": None}

    def kapi() -> Kapi:
        if durum["kapi"] is None:
            if kapi_fabrika:
                durum["kapi"] = kapi_fabrika()
            else:
                import config
                from exchange_client import ExchangeClient

                def _b(m):
                    try:
                        import bildirim
                        bildirim.gonder(m)
                    except Exception:
                        pass
                a = ayarlar()
                if a["ayri"]:   # madde 851: al-sat AYRI hesap (ALSAT_API_KEY / SECRET — şifreli kimlik carry-alsat.env)
                    a["mod"] = a["alsat_mod"]
                    ist = ExchangeClient(os.getenv("ALSAT_API_KEY", "").strip(), os.getenv("ALSAT_API_SECRET", "").strip(), mode=a["alsat_mod"],
                                         ozel_anahtar=False)
                else:
                    ist = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
                durum["kapi"] = Kapi(ist, ayar=a, bildir=_b)
        return durum["kapi"]

    def calistir(f):
        try:
            return jsonify({"ok": True, **f()})
        except Hata as e:
            return jsonify({"ok": False, "hata": e.mesaj, "kod": e.kod}), e.kod
        except Exception as e:           # Binance hatası vb. — mesaj kullanıcıya (anahtar içermez)
            m = re.sub(r"(signature|apiKey|api_key|X-MBX-APIKEY)=?\S*", "[gizli]", str(e))[:300]
            logger.error("panel işlem hatası: %s", m)
            return jsonify({"ok": False, "hata": binance_turkce(m)}), 502

    def govde() -> dict:
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            raise Hata("JSON gövde gerekli")
        return d

    @app.get("/durum")
    def r_durum():
        return calistir(lambda: kapi().durum())

    @app.get("/elle")
    def r_elle():
        return calistir(lambda: kapi().elle_ozet())

    @app.get("/gecmis")
    def r_gecmis():
        return calistir(lambda: gecmis(kapi()))

    @app.get("/pozisyon/<sem>")
    def r_poz(sem):
        return calistir(lambda: kapi().pozisyon(sem))

    @app.post("/onizle")
    def r_onizle():
        return calistir(lambda: kapi().onizle(govde()))

    @app.post("/emir")
    def r_emir():
        return calistir(lambda: kapi().emir(govde()))

    @app.post("/tpsl")
    def r_tpsl():
        return calistir(lambda: kapi().tpsl(govde()))

    @app.post("/kapat")
    def r_kapat():
        return calistir(lambda: kapi().kapat(govde()))

    @app.post("/iz")
    def r_iz():
        return calistir(lambda: kapi().iz(govde()))

    @app.post("/iptal")
    def r_iptal():
        return calistir(lambda: kapi().iptal(govde()))

    app.config["kapi"] = kapi
    return app


def _anlik_dongu(app) -> None:
    """MADDE 852: arka planda 5 dk'da bir al-sat özkaynak noktası (yalnız ayrı hesap)."""
    while True:
        try:
            k = app.config["kapi"]()
            if not k.ayar.get("ayri"):
                return
            anlik_kaydet(k)
        except Exception as e:
            logger.warning("al-sat anlık noktası yazılamadı: %s", str(e)[:200])
        time.sleep(ANLIK_ARA_SN)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="carry panel işlem kapısı (yalnız 127.0.0.1)")
    ap.add_argument("--port", type=int, default=int(os.getenv("CARRY_ISLEM_PORT", "8051")))
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from waitress import serve
    print(f"carry-islem: http://127.0.0.1:{a.port} (yalnız yerel; panel /api/islem/* buraya iletir)")
    app = uygulama()
    threading.Thread(target=_anlik_dongu, args=(app,), daemon=True).start()   # madde 852
    serve(app, host="127.0.0.1", port=a.port, threads=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
