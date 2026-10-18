"""Edge sağlık dedektörü testleri (madde 139).

NEDEN: dedektör iki yönde de pahalı hata yapabilir:
  - sağlıklı edge'i KAPATIRSA -> kâr kaybı (yanlış alarm)
  - ölü edge'i AÇIK TUTARSA  -> amacı yok (kaçırma)
Ve üçüncü, bu projeye özgü bir yol var: veri gelmediğinde sessizce
ya hep açık ya hep kapalı kalmak. Üçü de burada kilitlenir.
"""
import sys

import numpy as np

sys.path.insert(0, '.')
import carry_saglik as H

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


SAAT = 3600000
GUN = 24 * SAAT
SIMDI = 1_760_000_000_000


def dunya(n=40, gun=40, mod="kalici", olcek=1.0, aralik_saat=8, tohum=0):
    """Sahte funding geçmişi. mod:
       kalici  : her sembolün oranı sabit (+ küçük gürültü) -> edge VAR
       karisik : her ödemede oranlar semboller arasında yeniden dağılır
       """
    rng = np.random.default_rng(tohum)
    taban = np.linspace(-0.0006, 0.0006, n) * olcek
    g = {f"S{i}": [] for i in range(n)}
    t = SIMDI - gun * GUN
    while t <= SIMDI:
        if mod == "karisik":
            # HER ÖDEMEDE yeniden dağıt: kalıcılık TAMAMEN yok. (5 günlük
            # bloklarla karıştırmak, bloklar dedektörünkiyle hizalı olmadığı
            # için kısmi kalıcılık sızdırıyordu - IC 0.20, F +11bp. O durum
            # "edge öldü" değil "edge zayıfladı" demek; ayrıca test ediliyor.)
            p = np.random.default_rng(int(t // SAAT)).permutation(n)
            oranlar = taban[p]
        else:
            oranlar = taban
        for i in range(n):
            g[f"S{i}"].append((t, float(oranlar[i]
                                        + rng.normal(0, 0.00003) * olcek)))
        t += aralik_saat * SAAT
    return g


print("1) SAĞLIKLI DÜNYA -> SAGLIKLI (yanlış alarm yok)")
ic, f, d = H.metrikleri_hesapla(dunya(), SIMDI, 12)
durum, gerekce = H.saglik_durumu(ic, f, d)
kontrol("kalıcı funding'de durum SAGLIKLI", durum == "SAGLIKLI", f"({durum}: {gerekce})")
kontrol("IC yüksek (>0.8)", np.nanmean(ic) > 0.8, f"({np.nanmean(ic):.3f})")
kontrol("gölge kitap funding TOPLUYOR (F>0)", np.nanmean(f) > 0, f"({np.nanmean(f)})")
kontrol("IC ve F için tam PENCERE kadar blok üretildi",
        len(ic) == H.PENCERE and len(f) == H.PENCERE, f"({len(ic)}, {len(f)})")
kontrol("DISP şimdiki blok dahil PENCERE+1 değer", len(d) == H.PENCERE + 1, f"({len(d)})")

print("\n2) KALICILIK ÖLÜMÜ -> ARTIK KAPATMIYOR, UYARIYOR (madde 234)")
# MADDE 234: bu test eskiden "karisik funding -> BOZUK" bekliyordu,
# cunku IC kapiyi kapatiyordu. IC'nin ileriye donuk haber degeri
# OLCULDU ve YOK (Spearman 0,048, p=0,067; esiginin ALTINDA getiri
# ortalamanin USTUNDE, +%10,9 vs +%6,7). Kapinin 4 yildaki tek otmesi
# IC yuzundendi ve stratejinin 36 gunde +%25,5 yaptigi doneme denk
# geliyordu (tum pencerelerin 95. yuzdeligi).
# Madde 139'un KENDI kaydi da destekliyor: senaryo A'nin getiri faydasi
# -1,5 puan, t=-0,55, ANLAMSIZ.
# BU TESTI "DUZELTMEYIN": kalicilik olumunu kacirmak OLCULMUS bir secim.
ic, f, d = H.metrikleri_hesapla(dunya(mod="karisik"), SIMDI, 12)
durum, gerekce = H.saglik_durumu(ic, f, d)
kontrol("karışık funding'de IC düşüyor ama kapı KAPANMIYOR",
        durum != "BOZUK", f"({durum}: {gerekce})")
kontrol("IC düşüşü UYARI olarak gerekçeye yazılıyor",
        "UYARI" in gerekce or durum == "ISINMA", f"({gerekce})")
kontrol("uyarı 'kapatma ölçütü DEĞİL' diyor",
        "kapatma ölçütü DEĞİL" in gerekce or durum == "ISINMA")
kontrol("gerekçe IC'yi gösteriyor", "IC" in gerekce, f"({gerekce})")
kontrol("IC sıfıra yakın (|IC| < 0.2)", abs(np.nanmean(ic)) < 0.2, f"({np.nanmean(ic):.3f})")

print("\n2b) KISMİ KALICILIK -> alarm YOK (zayıflama ölüm değildir)")
def kismi(n=40, gun=40):
    taban = np.linspace(-0.0006, 0.0006, n)
    g = {f"S{i}": [] for i in range(n)}
    t = SIMDI - gun * GUN
    rng = np.random.default_rng(3)
    while t <= SIMDI:
        # oranın %50'si kalıcı, %50'si her ödemede rastgele
        p = np.random.default_rng(int(t // SAAT)).permutation(n)
        for i in range(n):
            g[f"S{i}"].append((t, 0.5 * taban[i] + 0.5 * taban[p[i]]
                               + rng.normal(0, 0.00003)))
        t += 8 * SAAT
    return g
ic, f, d = H.metrikleri_hesapla(kismi(), SIMDI, 12)
durum, gerekce = H.saglik_durumu(ic, f, d)
kontrol("yarı kalıcı funding'de SAGLIKLI (yanlış alarm yok)",
        durum == "SAGLIKLI", f"({durum}: {gerekce})")
# F, primin KALICI kısmını ölçmeli: yarı kalıcı dünyada tam dünyanın
# yaklaşık yarısı. (Rastgele yarı, 15 ödemenin toplamında ortalamaya
# iner ve sıralamayı bozmaz - bu yüzden IC değil F'ye bakılıyor.)
_, f_tam, _ = H.metrikleri_hesapla(dunya(), SIMDI, 12)
oran = np.nanmean(f) / np.nanmean(f_tam)
kontrol("F primin kalıcı payıyla orantılı (yarı kalıcı -> ~yarı F)",
        0.35 < oran < 0.65, f"(oran {oran:.2f})")

print("\n3) PRİM SIKIŞMASI -> BOZUK (sıralama aynı, büyüklük yok)")
ic, f, d = H.metrikleri_hesapla(dunya(olcek=0.02), SIMDI, 12)
durum, gerekce = H.saglik_durumu(ic, f, d)
kontrol("x0.02 sıkışmada durum BOZUK", durum == "BOZUK", f"({durum}: {gerekce})")
kontrol("gerekçe funding farkını (DISP) gösteriyor", "funding farki" in gerekce, f"({gerekce})")

print("\n4) YETERSİZ GEÇMİŞ -> ISINMA (ne alarm ne onay)")
ic, f, d = H.metrikleri_hesapla(dunya(gun=8), SIMDI, 12)
durum, _ = H.saglik_durumu(ic, f, d)
kontrol("8 günlük geçmişte ISINMA", durum == "ISINMA", f"({durum})")
durum, _ = H.saglik_durumu([], [], [])
kontrol("boş geçmişte ISINMA (çökmez)", durum == "ISINMA", f"({durum})")
ic, f, d = H.metrikleri_hesapla({}, SIMDI, 12)
kontrol("hiç sembol yokken çökmez, ISINMA",
        H.saglik_durumu(ic, f, d)[0] == "ISINMA")

print("\n5) ARALIK NORMALİZASYONU — canlı botla parite")
import carry_bot as cb
kay = [{"fundingRate": "0.0001", "fundingTime": 1700000000000 + i * s * SAAT}
       for s in [1] for i in range(6)]
y_bot = cb.yillik_funding(kay)
y_sag = H._yillik([(int(k["fundingTime"]), 0.0001) for k in kay])
kontrol("1 saatlik aralıkta dedektör = bot (alt sınır 4sa ikisinde de)",
        abs(y_bot - y_sag) < 1e-12, f"(bot {y_bot}, dedektör {y_sag})")
for s in [4, 8]:
    kay = [{"fundingRate": "0.0002", "fundingTime": 1700000000000 + i * s * SAAT}
           for i in range(6)]
    kontrol(f"{s} saatlik aralıkta dedektör = bot",
            abs(cb.yillik_funding(kay) - H._yillik(
                [(int(k["fundingTime"]), 0.0002) for k in kay])) < 1e-12)
ic4, f4, d4 = H.metrikleri_hesapla(dunya(aralik_saat=4), SIMDI, 12)
kontrol("4 saatlik ödeyen dünyada da SAGLIKLI",
        H.saglik_durumu(ic4, f4, d4)[0] == "SAGLIKLI")

print("\n6) KAPI — zaman bazlı histerezis")
k = {}
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 0)
kontrol("başlangıçta kapı açık", k["acik"])
k = H.kapi_guncelle_zamanli(k, "BOZUK", 1 * GUN)
kontrol("BOZUK görülünce anında kapanır", not k["acik"])
kontrol("kapanış zamanı kaydedildi", k["kapanis_ms"] == 1 * GUN)
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 2 * GUN)
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 11 * GUN)
kontrol("9 gün temiz yetmez (kapalı kalır)", not k["acik"])
k = H.kapi_guncelle_zamanli(k, "BOZUK", 11 * GUN + SAAT)
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 12 * GUN)
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 21 * GUN)
kontrol("arada BOZUK görülürse sayaç sıfırlanır", not k["acik"])
k = H.kapi_guncelle_zamanli(k, "SAGLIKLI", 22 * GUN)
kontrol("10 gün kesintisiz temiz -> yeniden açılır", k["acik"])
k2 = H.kapi_guncelle_zamanli({"acik": False, "temiz_bas_ms": None}, "ISINMA", 5 * GUN)
kontrol("ISINMA kapıyı DEĞİŞTİRMEZ (kapalıysa kapalı kalır)", not k2["acik"])
k3 = H.kapi_guncelle_zamanli(None, "ISINMA", 0)
kontrol("durum dosyası yoksa kapı açık başlar", k3["acik"])

print("\n7) EŞİKLER DEĞİŞTİRİLMEDİ (madde 139 kalibrasyonu)")
kontrol("IC eşiği 0.193", H.IC_ESIK == 0.193)
kontrol("F eşiği 0", H.F_ESIK == 0.0)
kontrol("DISP eşiği 2.86bp", abs(H.DISP_ESIK - 2.86e-4) < 1e-12)
kontrol("pencere 6 blok, toparlanma 2 blok", H.PENCERE == 6 and H.TOPARLANMA == 2)

print("\n" + "=" * 64)

print("\nSAAT HİZALAMASI (madde 185) - dedektör günün HER saatinde ölçebilmeli")
# 8 saatlik funding ızgarasında, dedektörün sinyal penceresi `_yillik`
# icin EN AZ IKI odeme icermeli. 12 saatlik pencere hizalamalarin
# yarisinda TEK odeme aliyordu -> ic/f bos -> ISINMA -> kapi acik,
# koruma yok. Bu test 8 hizalamanin HEPSINI dener.
import carry_bot as _cb
_blok = _cb.REBALANCE_HOURS


def _gecerli_blok(sinyal_saat, offset_saat):
    simdi = 1800000000000 + int(offset_saat * 3600000)
    geri = _blok * (H.PENCERE + 1) + max(sinyal_saat, 72.0) + 24
    bas = simdi - int(geri * 3600000)
    gec = {}
    for i in range(24):
        t = (bas // (8 * 3600000) + 1) * 8 * 3600000
        kay = []
        while t <= simdi:
            kay.append((t, 0.0001 * (i - 12)))
            t += 8 * 3600000
        gec[f"S{i}USDT"] = kay
    ic, f, d = H.metrikleri_hesapla(gec, simdi, 12, blok_saat=_blok,
                                     sinyal_saat=sinyal_saat)
    return sum(1 for x in ic if np.isfinite(x))


_sp = max(_cb.FUNDING_WINDOW_HOURS, 24.0)
_hepsi = [_gecerli_blok(_sp, o) for o in range(8)]
kontrol("dedektör 8 saat hizalamasının HEPSİNDE ölçüyor",
        min(_hepsi) >= H.PENCERE, f"({_hepsi})")
_eski = [_gecerli_blok(12.0, o) for o in range(8)]
kontrol("12 saatlik pencere GERÇEKTEN bozuktu (testin kendisi çalışıyor)",
        min(_eski) == 0, f"({_eski})")
kontrol("canlı botun dedektör penceresi >= 24 saat",
        _sp >= 24.0, f"({_sp})")


if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum saglik testleri gecti.")
