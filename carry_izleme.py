"""CARRY BOT CANLI İZLEME — backtest varsayımlarını GERÇEK veriyle ölçer.

NEDEN BU ARAÇ: backtest'in üç doğrulanmamış varsayımı var ve %92'lik
beklentinin tamamı bunların üstünde duruyor (madde 124):

  1. funding gerçekten tahsil ediliyor mu?  (gelirin ~%35'i)
  2. limit emirler doluyor mu?              (maliyet varsayımının yarısı)
  3. gerçek kayma %0.01-0.02 mi?

Bu araç Binance'in GELİR GEÇMİŞİ (income history) API'sinden hesabın
gerçek nakit akışını çeker ve backtest beklentisiyle karşılaştırır.
Tahmin yapmaz - borsanın kendi kayıtlarını okur.

KULLANIM:
    python carry_izleme.py              # son 7 gün
    python carry_izleme.py --gun 30     # son 30 gün
    python carry_izleme.py --gun 30 --csv rapor.csv

ÇIKIŞ KODLARI (madde 260 + MADDE 286):
    0 = DEVAM · 1 = İNCELE · 2 = DURDUR · **3 = ÖLÇÜLEMEDİ**
Kod 3, anahtar yok / borsaya ulaşılamadı demektir ve bir VERDİKT DEĞİLDİR.
Madde 286'dan önce bu durum ham bir AssertionError ile çöküp Python'un
1 kodunu veriyordu - yani "İNCELE" verdiktiyle birebir aynı.

NE ZAMAN ÇALIŞTIRMALI: bot en az 3-5 gün çalıştıktan sonra (bir tam
dilim döngüsü). Daha erken çalıştırmak yanıltıcı olur - funding 8
saatte bir ödeniyor ve ilk turlarda portföy henüz tam kurulmamış
oluyor (kademeli giriş, madde 123).
"""
from __future__ import annotations

import argparse
import sys
import time
from collections import defaultdict

import config
from exchange_client import ExchangeClient

# Backtest varsayımları (madde 113-124) - karşılaştırma için
# MADDE 233: funding beklentisi ARTIK BURADA TUTULMUYOR. Tek kanonik
# kaynak `carry_rapor` (madde 232'de ÖLÇÜLDÜ). İki dosyada iki ayrı
# sayı tutmak, bu projede zaten bir kere yanlış sayıya yol açtı.
try:
    from carry_rapor import (BEKLENEN_FUNDING_GUNLUK, BEKLENEN_FUNDING_TABAN,
                             rejim_tahmini)
except Exception:          # araç tek başına çalıştırılabilsin
    BEKLENEN_FUNDING_GUNLUK, BEKLENEN_FUNDING_TABAN = 0.001055, 0.000653

    def rejim_tahmini(x):
        return ("?", float("nan"))

BEKLENEN_FUNDING_PAYI = 0.488
"""Funding / net kâr oranı - YALNIZCA BİLGİ, alarm ÖLÇÜTÜ DEĞİL.

MADDE 233 - BU ORAN YAPISI GEREĞİ BOZUK BİR ÖLÇÜTTÜ. Eski değer 0,35
ve eşik "yarısının altı = uyarı" idi. İki sorun:

1. BAYAT: ölçülen oran tüm örnekte 0,488; düşük prim rejiminde 0,341,
   yüksek primde 0,652 (madde 231/232). 0,35 yalnızca DÜŞÜK rejime
   denk geliyor.
2. ASIL SORUN - KARARSIZ: paydası (net kâr), madde 214'e göre birbirini
   GÖTÜREN iki büyük sayının küçük farkı (funding +109,8 / ham fiyat
   -108,0). Aylık pencerede oranın dağılımı: p5 **-0,11**, medyan 0,44,
   p95 **+7,49**, ve 50 ayın 4'ünde net NEGATİF. Eski uyarı eşiği
   (0,175) SAĞLIKLI bir botta bile **ayların %26'sında** ötüyordu.

Yani bu, projede bulunan ÜÇÜNCÜ sürekli öten alarmdı (madde 177'nin
dersi: sürekli öten alarm kapatılır). Alarm, madde 232'nin MUTLAK
ölçütüne taşındı: funding/gün, sermaye oranı olarak, en kötü rejimin
tabanına karşı. O ölçüt kararlı ve 14 günde %100 güçlü (madde 216).
Oran yine yazdırılıyor çünkü rejim hakkında bilgi veriyor - ama hiçbir
karar ona bağlı değil."""
BEKLENEN_MAKER_ORANI = 0.90       # emirlerin ne kadarı maker olmalı
BEKLENEN_KOMISYON_ORANI = 0.0002  # maker %0.02
MAKER_ESIGI_KISA_TUTMA = 0.80     # madde 141: kısa tutma önerisi için
KOMISYON_ESIGI_KISA_TUTMA = 0.00025


def gelir_gecmisi(client: ExchangeClient, gun: int) -> list:
    """Binance gelir geçmişini çeker (sayfalama ile).

    Tipler: FUNDING_FEE, COMMISSION, REALIZED_PNL, TRANSFER...
    """
    bitis = int(time.time() * 1000)
    baslangic = bitis - gun * 86400 * 1000
    kayitlar = []
    imlec = baslangic
    for _ in range(50):                      # en fazla 50 sayfa
        try:
            p = client.client.futures_income_history(
                startTime=imlec, endTime=bitis, limit=1000)
        except Exception as e:
            print(f"[hata] gelir geçmişi alınamadı: {e}")
            break
        if not p:
            break
        kayitlar += p
        yeni = max(int(k["time"]) for k in p)
        if yeni <= imlec or len(p) < 1000:
            break
        imlec = yeni + 1
        time.sleep(0.3)
    return kayitlar


def islem_gecmisi(client: ExchangeClient, semboller: list, gun: int) -> list:
    """Gerçekleşen işlemleri çeker - maker/taker oranı için."""
    bitis = int(time.time() * 1000)
    baslangic = bitis - gun * 86400 * 1000
    out = []
    for i, s in enumerate(semboller):
        try:
            t = client.client.futures_account_trades(
                symbol=s, startTime=baslangic, endTime=bitis, limit=1000)
            out += t
        except Exception:
            pass
        if i % 20 == 19:
            time.sleep(0.5)
    return out


def rapor(client: ExchangeClient, gun: int, csv_yol: str = None) -> dict:
    print(f"\n{'=' * 66}")
    print(f"  CARRY BOT CANLI İZLEME — son {gun} gün")
    print(f"{'=' * 66}\n")

    # Toplam teminat (BFUSD gibi USDT dışı teminat dahil, madde 141).
    # Eski/sahte istemcilerde yoksa USDT bakiyesine düşer.
    _eq = getattr(client, "get_account_equity_usd", None)
    bakiye = _eq() if callable(_eq) else client.get_account_balance_usdt()
    pozlar = [p for p in client.get_open_positions()
              if abs(float(p.get("positionAmt", 0))) > 1e-12]
    uzun = sum(abs(float(p["positionAmt"]) * float(p.get("entryPrice") or 0))
               for p in pozlar if float(p["positionAmt"]) > 0)
    kisa = sum(abs(float(p["positionAmt"]) * float(p.get("entryPrice") or 0))
               for p in pozlar if float(p["positionAmt"]) < 0)

    print("PORTFÖY DURUMU")
    print(f"  bakiye            : {bakiye:,.2f} USDT")
    print(f"  açık pozisyon     : {len(pozlar)}  ({sum(1 for p in pozlar if float(p['positionAmt'])>0)} long / "
          f"{sum(1 for p in pozlar if float(p['positionAmt'])<0)} short)")
    print(f"  long tarafı       : {uzun:,.2f} USDT")
    print(f"  short tarafı      : {kisa:,.2f} USDT")
    if uzun + kisa > 0:
        dengesizlik = abs(uzun - kisa) / max(uzun, kisa)
        print(f"  brüt / bakiye     : {(uzun + kisa) / max(bakiye, 1e-9):.2f}x")
        print(f"  nötrlük sapması   : %{dengesizlik * 100:.1f}"
              f"{'   <-- UYARI: %10 üstü, portföy tek yönlü kalmış' if dengesizlik > 0.10 else '   (iyi)'}")

    kayitlar = gelir_gecmisi(client, gun)
    if not kayitlar:
        print("\n[!] Gelir kaydı bulunamadı. Bot henüz çalışmamış olabilir.")
        return {}

    toplam = defaultdict(float)
    for k in kayitlar:
        toplam[k.get("incomeType", "?")] += float(k.get("income", 0))

    funding = toplam.get("FUNDING_FEE", 0.0)
    komisyon = toplam.get("COMMISSION", 0.0)
    pnl = toplam.get("REALIZED_PNL", 0.0)
    net = funding + komisyon + pnl

    print(f"\nNAKİT AKIŞI ({gun} gün, borsanın kendi kayıtları)")
    print(f"  {'funding':<20}{funding:>+14,.4f} USDT")
    print(f"  {'komisyon':<20}{komisyon:>+14,.4f} USDT")
    print(f"  {'gerçekleşen K/Z':<20}{pnl:>+14,.4f} USDT")
    print(f"  {'-' * 34}")
    print(f"  {'NET':<20}{net:>+14,.4f} USDT   (%{net / max(bakiye, 1e-9) * 100:+.2f})")
    if gun > 0:
        yillik = (net / max(bakiye, 1e-9)) * (365.0 / gun) * 100
        print(f"  {'yıllık karşılığı':<20}{yillik:>+13.1f}%")

    print("\n=== VARSAYIM 1: FUNDING TAHSİL EDİLİYOR MU? ===")
    if funding > 0:
        print(f"  funding GELİR olarak geldi: {funding:+,.4f} USDT  ✓")
        # MADDE 233: KARAR, mutlak olcute bagli (gun basina, sermaye
        # orani) - oran degil. Oran kararsiz: paydasi birbirini goturen
        # iki buyuk sayinin kucuk farki (madde 214).
        if gun > 0 and bakiye > 0:
            gunluk = funding / (gun * bakiye)
            rj, bek = rejim_tahmini(gunluk)
            print(f"  günlük tahsilat: %{gunluk * 100:.4f} "
                  f"(en kötü rejim tabanı %{BEKLENEN_FUNDING_TABAN * 100:.4f}, "
                  f"harman %{BEKLENEN_FUNDING_GUNLUK * 100:.4f})")
            print(f"  → REJİM: {rj}   geçerli beklenti ~+%{bek:.0f}/yıl "
                  f"(madde 231)")
            _o = gunluk / BEKLENEN_FUNDING_TABAN
            if _o < 0.50:
                print(f"  [!!] tabanın %{_o * 100:.0f}'i - DURDUR, "
                      "API/hesap tarafında sorun ara (madde 232)")
            elif _o < 0.80:
                print(f"  [!] tabanın %{_o * 100:.0f}'i - sebebini bul; "
                      "gün 14+ ise bu ölçütün gücü %100 (madde 216)")
        if net > 0:
            pay = funding / net
            print(f"  (bilgi) net kârın %{pay * 100:.0f}'i funding'den; "
                  f"ölçülen aralık rejime göre %34-%65 - madde 233: bu oran "
                  "KARARSIZ, karar ölçütü DEĞİL")
    elif funding < 0:
        print(f"  [!!] FUNDING ÖDÜYORUZ: {funding:+,.4f} USDT")
        print("  Bu KRİTİK bir hatadır - stratejinin işareti ters olabilir.")
        print("  test_carry_bot.py'deki 'İŞARET YÖNÜ' testini çalıştırın.")
    else:
        print("  henüz funding ödemesi kaydedilmemiş (8 saatte bir olur,")
        print("  botun en az bir gün çalışması gerekir)")

    print("\n=== VARSAYIM 2: LİMİT EMİRLER DOLUYOR MU? ===")
    sem = sorted({p["symbol"] for p in pozlar})
    islemler = islem_gecmisi(client, sem, gun) if sem else []
    if islemler:
        maker = sum(1 for t in islemler if t.get("maker"))
        oran = maker / len(islemler)
        hacim = sum(float(t.get("quoteQty", 0)) for t in islemler)
        print(f"  toplam işlem      : {len(islemler)}")
        print(f"  maker olan        : {maker}  (%{oran * 100:.0f})")
        print(f"  beklenen          : ~%{BEKLENEN_MAKER_ORANI * 100:.0f}")
        if oran < 0.5:
            print("  [!] Emirlerin YARIDAN AZI maker - komisyon varsayımı")
            print("      bozuluyor. LIMIT_OFSET artırılmalı olabilir.")
        elif oran < BEKLENEN_MAKER_ORANI:
            print("  (beklenenin altında ama kabul edilebilir)")
        else:
            print("  ✓ beklenti karşılanıyor")
        if hacim > 0:
            gercek = abs(komisyon) / hacim
            print(f"\n=== VARSAYIM 3: GERÇEK KOMİSYON ORANI ===")
            print(f"  işlem hacmi       : {hacim:,.2f} USDT")
            print(f"  ödenen komisyon   : {abs(komisyon):,.4f} USDT")
            print(f"  gerçek oran       : %{gercek * 100:.4f}")
            print(f"  backtest varsayımı: %{BEKLENEN_KOMISYON_ORANI * 100:.4f} (maker)")
            # TUTMA SÜRESİ ÖNERİSİ (madde 141): funding avantajı hızla
            # söndüğü için maker maliyetiyle 3 günlük tutma, 5 günlükten
            # hem eğitim hem test döneminde daha çok funding - ücret
            # bırakıyor. Ama SADECE maker gerçekten tutuyorsa.
            if oran >= MAKER_ESIGI_KISA_TUTMA and gercek <= KOMISYON_ESIGI_KISA_TUTMA:
                # madde 145: kâr al + hisse filtresiyle yeniden ölçüldü. 3 gün
                # daha çok getiri veriyor ama Sharpe'ı İYİLEŞTİRMİYOR - yani
                # bir kâr artırma değil, risk artırma seçeneği.
                print("\n=== BİLGİ: KISA TUTMA ÖNKOŞULU SAĞLANDI (madde 145) ===")
                print(f"  maker oranı %{oran * 100:.0f} >= %{MAKER_ESIGI_KISA_TUTMA * 100:.0f} ve")
                print(f"  gerçek komisyon %{gercek * 100:.4f} <= %{KOMISYON_ESIGI_KISA_TUTMA * 100:.4f}")
                # MADDE 179: yeni yapılandırmada (6+6, kâr al %40, havuz 3.0)
                # tutma süresi YENİDEN ölçüldü ve 5 gün TEPE çıktı.
                print("  Backtest (güncel ayar, maker maliyeti, 6+6):")
                print("    5 gün: +%90.1/yıl  Sharpe 2.63   <- mevcut, TEPE")
                print("    4 gün: +%93.6/yıl  Sharpe 2.55")
                print("    3 gün: +%92.6/yıl  Sharpe 2.34")
                print("    2 gün: +%102.2/yıl Sharpe 2.30")
                print("  Kısa tutma daha çok getiri ama daha DÜŞÜK Sharpe verir")
                print("  (devir maliyeti). Değiştirmeye gerek YOK.")
            if gercek > BEKLENEN_KOMISYON_ORANI * 1.5:
                print(f"  [!] Varsayımın {gercek / BEKLENEN_KOMISYON_ORANI:.1f} KATI. "
                      "Backtest getirisi iyimser.")
                print("      BNB ile komisyon ödemeyi açın (%10 indirim) ve")
                print("      maker oranını yükseltin.")
            else:
                print("  ✓ varsayım tutuyor")
    else:
        print("  işlem kaydı yok (bot henüz emir göndermemiş olabilir)")

    # ---------------------------------------- MADDE 216: KÂR AL ULAŞMA ORANI
    # Madde 214: kârın TAMAMI kâr-al hasadından geliyor (funding +109,8 ile
    # ham fiyat -108,0 birbirini götürüyor, TP +210,5). Yani TP oranı kâr
    # motorunun en doğrudan göstergesi. Madde 216'da gücü ölçüldü: LONG
    # tarafı 30 günde %95 (toplam getiri aynı sürede %15 - madde 151).
    print(f"\n{'-' * 66}")
    print("KÂR AL ULAŞMA ORANI (madde 216) — kâr motorunun doğrudan göstergesi")
    try:
        import carry_bot as _cb
        _tp = _cb.tp_defteri_oku(gun=gun)
        # Beklenen dolum SAYISI: her tur bir dilim (n+n bacak) kurulur,
        # dilim 5 gunde bir yenilenir -> gunde NDILIM/5 dilim x n bacak.
        _n = _cb.N_LEGS
        _dilim_gun = _cb.N_DILIM / (_cb.REBALANCE_HOURS / 24.0)
        _bacak_l = _bacak_s = _dilim_gun * _n * gun
        _bek_l = _bacak_l * _cb.BEKLENEN_TP_LONG
        _bek_s = _bacak_s * _cb.BEKLENEN_TP_SHORT
        print(f"  dönem            : {gun:.0f} gün")
        print(f"  kurulan bacak    : ~{_bacak_l:.0f} long + ~{_bacak_s:.0f} short")
        for _t, _g, _b, _o in (("LONG", _tp["LONG"], _bek_l, _cb.BEKLENEN_TP_LONG),
                               ("SHORT", _tp["SHORT"], _bek_s, _cb.BEKLENEN_TP_SHORT)):
            _oran = _g / _b * _o if _b > 0 else float("nan")
            print(f"  {_t:5s} TP dolumu  : {_g} adet   beklenen ~{_b:.0f} "
                  f"(oran %{_oran*100:.1f} vs beklenen %{_o*100:.1f})")
        # MADDE 292: DÜŞÜK DOLUMUN İKİ AYRI SEBEBİ VAR, SUÇLAMADAN ÖNCE AYIR.
        # Eski kod düşük dolumu görünce doğrudan "kâr motoru çalışmıyor
        # olabilir" diyordu - yani 291 maddelik stratejiyi şüpheli ilan
        # ediyordu. Aynı belirtiyi hiç KONULMAMIŞ emirler de üretir ve o bir
        # İCRA arızasıdır. Madde 286'nın yasası ("ölçemedim" ile "ölçtüm,
        # şüpheli" ayrı kodlar olmalı) canlı yüzeyde de geçerli.
        try:
            _ku = _cb.tp_kurulum_oku(gun=gun)
        except Exception:
            _ku = {"tur": 0, "hedeflenen": 0, "kurulan": 0, "olculemedi": 0,
                   "oran": float("nan")}
        if _ku["tur"] > 0:
            _o = _ku["oran"]
            print(f"  TP KONMA oranı   : {_ku['kurulan']}/{_ku['hedeflenen']} "
                  f"(%{_o * 100:.1f}) · {_ku['tur']} tur")
            if _ku.get("olculemedi"):
                print(f"      ({_ku['olculemedi']} turda pozisyonlar hiç "
                      f"OKUNAMADI - orana katılmadı, madde 286)")
        else:
            print("  TP KONMA oranı   : defter yok (madde 292 öncesi tur ya da "
                  "henüz hiç tur koşmadı)")
        _kurulum_bozuk = (_ku["tur"] > 0 and _ku["hedeflenen"] > 0
                          and _ku["oran"] < 0.95)
        if sum(_tp.values()) == 0:
            print("  [i] Dolum defteri BOŞ. İlk 5 gün normal (kitap kuruluyor);")
            print("      daha sonra da boşsa `carry_tp.csv` yazılamıyor olabilir.")
        elif _kurulum_bozuk:
            print("  [!] TP EMİRLERİ KONULAMIYOR — bu bir PİYASA bulgusu DEĞİL,")
            print("      bir İCRA arızasıdır. Dolum oranına BAKMAYIN: dolmayan")
            print("      emir zaten konulmamış. Önce logdaki 'KÂR AL EMRİ")
            print("      KONULAMADI' satırlarının sebebini çözün (hız sınırı,")
            print("      hassasiyet, asgari nominal). Strateji şüpheli DEĞİL.")
        elif _bek_l > 3 and _tp["LONG"] < 0.4 * _bek_l:
            print("  [!] LONG TP dolumu beklenenin YARISINDAN AZ **ve emirler")
            print("      KONULMUŞ** (konma oranı ≥%95). Yani bu gerçekten bir")
            print("      piyasa/varsayım bulgusu: kâr motoru çalışmıyor olabilir")
            print("      - getiriden ÇOK daha hızlı haber verir (30 günde %95 güç).")
        else:
            print("  ✓ TP dolumu beklenen aralıkta")
        print("  Güç (madde 216): funding tahsilatı 14 günde %100 ·")
        print("  LONG TP oranı 30 günde %95 · toplam getiri 30 günde %15")
    except Exception as _e:
        print(f"  [hata] TP defteri okunamadı: {_e}")

    if csv_yol:
        try:
            import csv as _csv
            with open(csv_yol, "w", newline="", encoding="utf-8") as fh:
                w = _csv.writer(fh)
                w.writerow(["zaman", "tip", "sembol", "tutar"])
                for k in sorted(kayitlar, key=lambda x: int(x["time"])):
                    w.writerow([k["time"], k.get("incomeType"),
                                k.get("symbol", ""), k.get("income")])
            print(f"\nHam kayıtlar yazıldı: {csv_yol}")
        except OSError as e:
            print(f"[hata] CSV yazılamadı: {e}")

    print(f"\n{'=' * 66}")
    print("  Bu rapor TAHMİN DEĞİL - borsanın kendi kayıtlarıdır.")
    print("  Backtest ile arasındaki fark, backtest'in hata payıdır.")
    print(f"{'=' * 66}\n")
    return {"bakiye": bakiye, "funding": funding, "komisyon": komisyon,
            "pnl": pnl, "net": net, "pozisyon": len(pozlar)}


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gun", type=int, default=7)
    ap.add_argument("--csv", default=None, help="ham kayıtları CSV'ye yaz")
    a = ap.parse_args()

    # MADDE 286: "OLCEMEDIM" ile "OLCTUM, SUPHELI" AYRI KODLAR OLMALI.
    # Bu arac anahtar yokken `rapor()` icinde ham AssertionError ile
    # cokuyordu ve Python cikis kodu 1 veriyordu - yani madde 260'in
    # "1 = INCELE" verdiktiyle BIREBIR AYNI. Gozetimsiz bir 14. gun
    # kontrolu icin bu, "funding tahsil edilmiyor" ile "anahtari
    # export etmeyi unuttum"u ayirt edemez demekti (madde 211'in
    # sessiz-yanlis-sinyal sinifi). Artik kod 3 = OLCULEMEDI.
    if not config.API_KEY or not config.API_SECRET:
        print("=" * 66)
        print("ÖLÇÜLEMEDİ — API anahtarı yok.")
        print("  BINANCE_API_KEY / BINANCE_API_SECRET ortam değişkeni YOK.")
        print("  Anahtar dosyaya YAZILMAZ - `export` ile verin.")
        print("  (çıkış kodu 3 = ÖLÇÜLEMEDİ; 1 = İNCELE verdiktiyle"
              " KARIŞTIRILMAMALI)")
        print("=" * 66)
        return 3

    client = ExchangeClient(config.API_KEY, config.API_SECRET,
                            mode=getattr(config, "MODE", "demo"))
    try:
        d = rapor(client, a.gun, a.csv)
    except Exception as e:                      # baglanti/izin/bolge hatasi
        print("=" * 66)
        print("ÖLÇÜLEMEDİ — borsa raporu alınamadı: %s: %s"
              % (type(e).__name__, e))
        print("  Bu bir VERDİKT DEĞİL. Anahtar izinleri, IP kısıtı ve ağ")
        print("  erişimini kontrol edip tekrar çalıştırın.")
        print("  (çıkış kodu 3 = ÖLÇÜLEMEDİ)")
        print("=" * 66)
        return 3

    # MADDE 260: ON KAYITLI CANLI KARAR. Bu arac eskiden yalnizca TESHIS
    # basiyordu ve her halde 0 ile cikiyordu - yani gozetimsiz bir 14. gun
    # kontrolu ona karar baglayamiyordu. Karar artik KOD: canli_karar.py.
    # Cikis kodu: 0 DEVAM · 1 INCELE · 2 DURDUR.
    try:
        import canli_karar as _ck
        bakiye = d.get("bakiye") or 0.0
        fon = ((d.get("funding") or 0.0) / (a.gun * bakiye)
               if a.gun > 0 and bakiye > 0 else None)
        getiri = (((d.get("net") or 0.0) / bakiye) * (365.0 / a.gun) * 100
                  if a.gun > 0 and bakiye > 0 else None)
        h = _ck.canli_gecer_mi(a.gun, funding_gunluk=fon,
                               dusus=d.get("dusus"), toplam_getiri=getiri)
        print()
        _ck.yaz(h)
        return _ck.cikis_kodu(h)
    except Exception as e:                      # karar ARACI raporu bozmaz
        print("\n[!] ön kayıtlı karar hesaplanamadı: %s: %s"
              % (type(e).__name__, e))
        return 0


if __name__ == "__main__":
    sys.exit(main())
