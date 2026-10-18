"""FUNDING PENCERESİ (OLAY) MODÜLÜ — madde 166.

NE YAPAR: funding ödemesinin gerçekleştiği ANIN etrafında, sadece
birkaç dakika pozisyonda kalır. Ödemeyi toplar, fiyat riskine neredeyse
hiç maruz kalmaz.

NEDEN AYRI BİR DOSYA: ana bot (`carry_bot.py`) günde bir kez çalışır ve
5 gün tutar. Bu modül dakika hassasiyetinde çalışır. İkisini aynı
döngüye sokmak ana botu kırılgan yapardı; bu yüzden AYRI SÜREÇ olarak
çalışır ve ana botun kodunu değiştirmez.

ZAMANLAMA — STRATEJİNİN TAMAMI BURADA (madde 166.3, 1 dakikalık
gerçek veriyle, 1.095 olay, iki bağımsız örnek):

    giriş     GTX doluluk   net/olay (iç)   net/olay (dış)
    T−1 dk       %87          +58.4 bp        +34.3 bp
    T−2 dk       %94          +42.8 bp        +19.1 bp
    T−5 dk       %96          +25.3 bp         +7.2 bp
    T−30 dk      %99          −19.6 bp        −44.3 bp   <-- ZARAR

Funding her durumda cebe giriyor (+41…+62 bp); fark tamamen GİRİŞ
zamanlamasından geliyor. Derin negatif funding'li coin sıkışma
hâlindedir - ödemeden yarım saat önce long açmak sıkışmanın tepesinden
almaktır. BU YÜZDEN `ONCE_SN` BÜYÜTÜLMEMELİDİR. 60 saniye tasarımın
kendisidir, ayarlanabilir bir konfor değil.

ANA BOTLA BİRLİKTE ÇALIŞMA (ölçüldü: 7.863 olay):
  - olayların %79.4'ü ana kitapta AYNI yönde  -> pozisyon birkaç
    dakikalığına büyür, sonra eski hâline döner. Zararsız.
  - %16.5'inde ana kitapta pozisyon YOK       -> temiz yeni pozisyon.
  - %4.1'i ana kitaba TERS                    -> ana bacağın bir
    kısmını KAPATIRDI. Bu modül böyle emirleri AÇMAZ (`ters_ele`).

İki mekanik koruma daha:
  1. Emirler `OLAY_ONEK` ile etiketlenir; `carry_bot.bayat_emirleri_temizle`
     bu öneki taşıyan emirlere DOKUNMAZ.
  2. Pozisyon açıkken kilit dosyası tutulur; ana bot o sırada tur
     atmaz (ikisi aynı dakikada kitaba dokunmaz).
"""
from __future__ import annotations

import json
import logging
import os
import time

logger = logging.getLogger(__name__)

# --------------------------------------------------------------- ayarlar
PAY = float(os.getenv("CARRY_OLAY_PAY", "0.0"))
"""Sermayenin ne kadarı bu modüle ayrılsın. **VARSAYILAN 0 = KAPALI.**

Ölçüldü (madde 166.1): %80 ana + %20 olay, 1.15x kaldıraçla
+%56.9 / Sharpe 2.20 / düşüş −%13.1 (taban +%55.5 / 2.13 / −%14.7).
Yani aynı getiride ~1.6 puan daha az düşüş.

MADDE 277 — VARSAYILAN DÜZELTİLDİ (gerçek bir kusurdu). Bu satırın
varsayılanı **0.20** idi, oysa aşağıdaki `ESIK` belgesi, `KAR_HARITASI.md`
ve bu modülün kendi uyarısı üç yerde "kurulu, `CARRY_OLAY_PAY=0` ile
kapalı" diyordu. `python carry_olay.py` çevre değişkeni verilmeden
çalıştırılırsa sermayenin **%20'si**, projenin kendi belgesinin
"açılmadan önce yeniden ölçülmeli" dediği bir kola gidiyordu. Madde
217'nin sınıfı (ayarın yanındaki bayat talimat) ama daha kötüsü: belge
ile kod AYNI ayar hakkında ters şey söylüyordu. Varsayılan artık 0 ve
ön uçuş denetimi bunu kontrol ediyor."""

ESIK = float(os.getenv("CARRY_OLAY_ESIK", "0.0020"))
"""Ödeme başına asgari |funding| oranı (0.0020 = 20bp).

Eşik taraması (madde 166.1): 5bp Sh 0.88 | 10bp 0.93 | **20bp 1.18** |
30bp 1.16 | 100bp 0.78. 20-30bp bandı düz; uçlar kötü."""

MAKS = int(os.getenv("CARRY_OLAY_MAKS", "6"))
"""Her tarafta en fazla kaç bacak.

MADDE 180: ana kitap 12+12'den 6+6'ya inince (madde 177) burası da 6'ya
çekildi - iki yapının bacak büyüklüğü aynı mertebede kalsın diye.

UYARI: bu modülün ölçülen faydası (madde 166: aynı getiride 1.6 puan
daha az düşüş) ESKİ ana yapılandırmaya (12+12, kâr al %70, havuz 2.0)
karşı hesaplanmıştı. Ana strateji +%52'den +%92'ye çıktığı için o
karşılaştırma ARTIK GEÇERSİZ; modül açılmadan önce yeniden ölçülmeli.
Varsayılan zaten kapalı (CARRY_OLAY_PAY=0)."""

ONCE_SN = int(os.getenv("CARRY_OLAY_ONCE_SN", "60"))
"""Ödemeden kaç saniye ÖNCE emir konsun. Yukarıdaki tabloya bakın:
bu sayıyı büyütmek stratejiyi ÖLDÜRÜR."""

CIK_DK = float(os.getenv("CARRY_OLAY_CIK_DK", "5"))
"""Ödemeden kaç dakika sonra çıkılsın. Ölçüm: çıkışı uzatmak zarar
vermiyor (T+5 / T+15 / T+60 birbirine yakın), giriş kritik."""

OFS = float(os.getenv("CARRY_OLAY_OFS", "0.0005"))
"""Post-only (GTX) emrin fiyattan uzaklığı."""

PIYASA_YEDEK = os.getenv("CARRY_OLAY_PIYASA", "1") not in ("0", "false", "False")
"""GTX dolmazsa piyasa emri kullanılsın mı.

ESKİ İDDİA (madde 166): "dolmayanlar taker'a düşse bile funding ücretin
kat kat üstünde (+57.1 / +32.2 bp)."

MADDE 277 — İŞARET YANLIŞ, YÖN DOĞRU. 23.609 olayda gerçek icrayla:
dolmayanlar GERÇEKTEN daha iyi (fiyat +9,15 bp lehte, net −26,06) ama
dolanlar −50,25 → **ikisi de negatif.** Üstelik maker dolumu (%98,3)
ters seçilimin KENDİSİ: limit, fiyat sana doğru geldiği için doluyor ve
fiyat gelmeye devam ediyor; dolmayanlarda fiyat limitten KAÇMIŞ.
Kol ÖLÜ (bkz. `arastirma_olay_icra.py`), bu ayar PAY=0 iken etkisiz."""

ONEK = "OLAY"
"""Emir etiketi. Ana botun bayat emir temizliği bu öneki atlar."""

KILIT = os.getenv("CARRY_OLAY_KILIT", "olay_kilit.json")
DURUM = os.getenv("CARRY_OLAY_DURUM", "olay_durum.json")


# ----------------------------------------------------------- saf mantık
def adaylar(mark: list, simdi_ms: int, pencere_sn: int = None,
            esik: float = None) -> list:
    """`futures_mark_price()` çıktısından bu turda işlem görecek adaylar.

    Aday olmak için: bir sonraki ödeme `pencere_sn` içinde olmalı VE
    son gerçekleşen funding oranı eşiği geçmeli.

    NEDENSELLİK: ödemenin BÜYÜKLÜĞÜ bilinmiyor; tahmin olarak son
    gerçekleşen oran (`lastFundingRate`) kullanılıyor. Ölçüldü: tahmin
    ile gerçekleşen arasındaki korelasyon 0.575, ve tahmini eşiği geçen
    olayların %76.8'inde gerçekten ödeme oluyor.

    Döner: [(sembol, yön, oran)] — yön +1 LONG (negatif funding alırız),
    −1 SHORT (pozitif funding alırız).
    """
    pencere = ONCE_SN if pencere_sn is None else pencere_sn
    e = ESIK if esik is None else esik
    out = []
    for m in mark or []:
        try:
            sem = m["symbol"]
            oran = float(m["lastFundingRate"])
            sonraki = int(m["nextFundingTime"])
        except (KeyError, TypeError, ValueError):
            continue
        if sonraki <= 0:
            continue
        kalan = (sonraki - simdi_ms) / 1000.0
        # Geçmişte kalanı ya da penceredeen uzak olanı alma. Alt sınır 0:
        # ödeme anı GEÇTİYSE girmek anlamsız, ödemeyi alamayız.
        if not (0 < kalan <= pencere):
            continue
        if abs(oran) < e:
            continue
        out.append((sem, 1 if oran < 0 else -1, oran))
    return out


def secim(aday: list, maks: int = None) -> list:
    """Her taraftan en uç `maks` adayı seçer."""
    m = MAKS if maks is None else maks
    uzun = sorted([a for a in aday if a[1] > 0], key=lambda a: a[2])[:m]
    kisa = sorted([a for a in aday if a[1] < 0], key=lambda a: -a[2])[:m]
    return uzun + kisa


def ters_ele(sec: list, mevcut: dict) -> tuple[list, list]:
    """Ana kitaba TERS düşen adayları eler (döner: kalanlar, elenenler).

    Tek yönlü (one-way) modda aynı sembolde ters emir, ana botun
    pozisyonunun bir kısmını KAPATIR. Ölçüldü: olayların %4.1'i bu
    durumda. Bedeli küçük, riski büyük - elenir.
    """
    kalan, elenen = [], []
    for sem, yon, oran in sec:
        v = mevcut.get(sem, 0.0)
        if v and (v > 0) != (yon > 0):
            elenen.append(sem)
        else:
            kalan.append((sem, yon, oran))
    return kalan, elenen


def bacak_usd(sermaye: float, n_secili: int = 0, pay: float = None,
              maks: int = None) -> float:
    """SABİT bacak büyüklüğü = sermaye * pay / (2 * maks).

    KRİTİK: `sermaye*pay/n` DEĞİL. İlk denemede öyle yazılmıştı; sinyal
    sayısı 2'ye düştüğünde her bacak kitabın yarısı oluyordu ve tek bir
    coin hesabı siliyordu (backtest'te −%99 düşüş). Az sinyal varsa
    maruziyet AZALIR, yoğunlaşmaz.
    """
    p = PAY if pay is None else pay
    m = MAKS if maks is None else maks
    return max(0.0, sermaye) * p / (2 * max(1, m))


def emir_etiketi(sem: str, simdi_ms: int) -> str:
    """Ana botun temizliğinden korunacak emir kimliği."""
    return f"{ONEK}{int(simdi_ms) % 10**10}{sem[:6]}"[:36]


def olay_emri_mi(emir: dict) -> bool:
    """Bir açık emir bu modüle mi ait? (ana bot bunu atlar)"""
    try:
        return str(emir.get("clientOrderId") or "").startswith(ONEK)
    except AttributeError:
        return False


# ------------------------------------------------------------ kilit/durum
def kilit_yaz(yol: str = None, semboller: list = None) -> None:
    y = yol or KILIT
    try:
        with open(y, "w", encoding="utf-8") as fh:
            json.dump({"zaman": time.time(), "semboller": list(semboller or ())}, fh)
    except OSError as e:
        logger.warning("olay kilidi yazılamadı: %s", e)


def kilit_sil(yol: str = None) -> None:
    try:
        os.remove(yol or KILIT)
    except OSError:
        pass


def kilit_var(yol: str = None, azami_yas_sn: float = 900.0) -> bool:
    """Kilit taze mi? BAYAT kilit (süreç çöktü) yok sayılır - aksi halde
    ana bot sonsuza kadar bloke olurdu."""
    y = yol or KILIT
    try:
        with open(y, encoding="utf-8") as fh:
            d = json.load(fh)
        return (time.time() - float(d.get("zaman", 0))) < azami_yas_sn
    except (OSError, ValueError, TypeError):
        return False


# ----------------------------------------------------------- yürütme
def _limit(fiyat: float, yon: int, hassasiyet: int, ofs: float = None) -> str:
    """Post-only için fiyattan UZAK taraf: ALIŞ altına, SATIŞ üstüne."""
    o = OFS if ofs is None else ofs
    p = fiyat * (1 - o) if yon > 0 else fiyat * (1 + o)
    return f"{p:.{hassasiyet}f}"


def ac(client, sec: list, bacak: float, simdi_ms: int = None) -> dict:
    """Seçilen bacakları GTX ile açar. Döner: {sembol: (yön, miktar)}."""
    simdi_ms = simdi_ms or int(time.time() * 1000)
    acilan = {}
    for sem, yon, _oran in sec:
        try:
            pr = client.get_symbol_precision(sem)
            fiyat = float(client.client.futures_symbol_ticker(symbol=sem)["price"])
            miktar = round(bacak / fiyat, pr["quantity_precision"])
            if miktar <= 0 or miktar * fiyat < 5.0:
                continue
            client.client.futures_create_order(
                symbol=sem, side="BUY" if yon > 0 else "SELL", type="LIMIT",
                timeInForce="GTX", quantity=miktar,
                price=_limit(fiyat, yon, pr.get("price_precision", 2)),
                newClientOrderId=emir_etiketi(sem, simdi_ms))
            acilan[sem] = (yon, miktar)
        except Exception as e:
            logger.warning("olay: %s emri konamadı: %s", sem, e)
    return acilan


def dolanlar(client, acilan: dict) -> dict:
    """Gerçekten pozisyona dönüşenler (kısmi dolum dahil, borsadan okunur)."""
    out = {}
    try:
        poz = {p["symbol"]: float(p["positionAmt"]) for p in client.get_open_positions()}
    except Exception as e:
        logger.warning("olay: pozisyonlar okunamadı: %s", e)
        return {}
    for sem, (yon, miktar) in acilan.items():
        v = poz.get(sem, 0.0)
        # Ana botun pozisyonu da aynı sembolde olabilir; bizim payımız
        # EN FAZLA açtığımız miktardır ve YÖNÜMÜZDE olmalıdır.
        if v and (v > 0) == (yon > 0):
            out[sem] = (yon, min(abs(v), miktar))
    return out


def kapat(client, acik: dict, piyasa_yedek: bool = None) -> int:
    """Açık olay bacaklarını kapatır: önce GTX, dolmazsa piyasa."""
    yedek = PIYASA_YEDEK if piyasa_yedek is None else piyasa_yedek
    kapanan = 0
    for sem, (yon, miktar) in acik.items():
        ters = "SELL" if yon > 0 else "BUY"
        try:
            pr = client.get_symbol_precision(sem)
            fiyat = float(client.client.futures_symbol_ticker(symbol=sem)["price"])
            client.client.futures_create_order(
                symbol=sem, side=ters, type="LIMIT", timeInForce="GTX",
                quantity=miktar, price=_limit(fiyat, -yon, pr.get("price_precision", 2)),
                reduceOnly=True, newClientOrderId=emir_etiketi(sem, int(time.time() * 1000)))
            kapanan += 1
        except Exception as e:
            logger.warning("olay: %s GTX çıkışı konamadı: %s", sem, e)
            if yedek:
                try:
                    client.close_position(sem, ters, miktar)
                    kapanan += 1
                except Exception as e2:
                    logger.error("olay: %s KAPATILAMADI: %s", sem, e2)
    return kapanan


def artik_temizle(client, acik: dict) -> int:
    """Çıkış GTX'i dolmadıysa kalanı PİYASA ile kapatır (pozisyon
    penceresinden SONRA açık kalmamalı - bu modülün tek kuralı budur)."""
    if not PIYASA_YEDEK:
        return 0
    kalan = dolanlar(client, acik)
    for sem, (yon, miktar) in kalan.items():
        try:
            client.cancel_all_open_orders(sem)
            client.close_position(sem, "SELL" if yon > 0 else "BUY", miktar)
        except Exception as e:
            logger.error("olay: %s artığı kapatılamadı: %s", sem, e)
    return len(kalan)


def bir_olay(client, mark: list = None, simdi_ms: int = None) -> dict:
    """Tek bir ödeme penceresini baştan sona yürütür."""
    simdi_ms = simdi_ms or int(time.time() * 1000)
    if mark is None:
        mark = client.client.futures_mark_price()
    aday = adaylar(mark, simdi_ms)
    if not aday:
        return {"aday": 0}
    sec = secim(aday)
    try:
        mevcut = {p["symbol"]: float(p["positionAmt"])
                  for p in client.get_open_positions()}
    except Exception as e:
        # Ana kitabı OKUYAMIYORSAK ters emir riskini alamayız - tur atlanır.
        logger.warning("olay: mevcut pozisyonlar okunamadı (%s) - tur atlandı", e)
        return {"atlandi": "pozisyon"}
    sec, elenen = ters_ele(sec, mevcut)
    if elenen:
        logger.info("olay: ana kitaba TERS %d sembol elendi: %s",
                    len(elenen), ", ".join(elenen[:5]))
    if not sec:
        return {"aday": len(aday), "secili": 0}
    sermaye = client.get_account_equity_usd()
    bacak = bacak_usd(sermaye, len(sec))
    kilit_yaz(semboller=[s for s, _, _ in sec])
    try:
        acilan = ac(client, sec, bacak, simdi_ms)
        # Ödeme anını GEÇ: pozisyon T anında açık olmalı.
        hedef = min(m["nextFundingTime"] for m in mark
                    if m.get("symbol") in acilan) if acilan else None
        if hedef:
            time.sleep(max(0.0, (int(hedef) - time.time() * 1000) / 1000.0 + 2.0))
        acik = dolanlar(client, acilan)
        logger.info("olay: %d emir, %d bacak doldu (bacak %.2f USD)",
                    len(acilan), len(acik), bacak)
        time.sleep(max(0.0, CIK_DK * 60.0))
        kapat(client, acik)
        time.sleep(30.0)
        artan = artik_temizle(client, acik)
    finally:
        kilit_sil()
    return {"aday": len(aday), "secili": len(sec), "acilan": len(acilan),
            "dolan": len(acik), "elenen": len(elenen), "artan": artan}


def dongu(client, bekleme_sn: float = 20.0, tur: int = 0) -> None:
    """Sürekli döngü: her `bekleme_sn` saniyede bir ödeme penceresi arar."""
    n = 0
    while tur <= 0 or n < tur:
        try:
            mark = client.client.futures_mark_price()
            if adaylar(mark, int(time.time() * 1000)):
                s = bir_olay(client, mark)
                logger.info("olay turu bitti: %s", s)
                n += 1
        except Exception as e:
            logger.error("olay döngüsü hatası: %s", e)
        time.sleep(bekleme_sn)
