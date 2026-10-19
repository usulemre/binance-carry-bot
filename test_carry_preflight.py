"""CARRY PREFLIGHT TESTLERİ (madde 217).

Bu dosyanın varlık sebebi: `CANLIYA_CIKIS.md` madde 182'nin rakamlarını
taşımaya devam ediyordu (madde 209 onları çürüttükten sonra bile), bacak
formülü 3 kat yanlıştı, "günde bir tur / 5 dilim / 12+12 bacak" diyordu.

**Bayat bir TALİMAT, bayat bir AYARDAN daha tehlikelidir: ayarı kod
denetler, talimatı kimse denetlemez.** Bu testler o boşluğu kapatır -
belgedeki sayıların koddan sapması KIRMIZI verir.
"""
import os
import re
import sys

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


R = os.path.dirname(os.path.abspath(__file__))
import carry_bot as cb
import carry_preflight as pf

print("1) PREFLIGHT YEREL MODDA ÇALIŞIYOR")
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0})
pf._satirlar.clear()
pf.kontrol_ayarlar()
pf.kontrol_parite()
pf.kontrol_referans()
pf.kontrol_defterler()
kontrol("yerel kontroller HATA vermiyor", pf._sayac[pf.HATA] == 0,
        f"({[s for s in pf._satirlar if s[1] == pf.HATA]})")
kontrol("en az 6 kontrol çalıştı", len(pf._satirlar) >= 6,
        f"({len(pf._satirlar)})")

print("\n2) AYAR SAPMASI YAKALANIYOR")
_eski = cb.FUNDING_WINDOW_HOURS
cb.FUNDING_WINDOW_HOURS = 8.0
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_ayarlar()
kontrol("pencere 8 saate çekilirse HATA", pf._sayac[pf.HATA] >= 1)
kontrol("gerekçe madde 209'u ve doğru değeri söylüyor",
        any("209" in m and "48" in m for _, d, m in pf._satirlar if d == pf.HATA),
        f"({[m for _, d, m in pf._satirlar if d == pf.HATA]})")
cb.FUNDING_WINDOW_HOURS = _eski
_eskin = cb.N_DILIM
cb.N_DILIM = 5
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_ayarlar()
kontrol("dilim sayısı 5'e düşerse HATA (madde 184)", pf._sayac[pf.HATA] >= 1)
cb.N_DILIM = _eskin
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_ayarlar()
kontrol("ayar geri gelince yine TAMAM", pf._sayac[pf.HATA] == 0)

print("\n3) PARİTE KIRIĞI YAKALANIYOR")
cb.FUNDING_WINDOW_HOURS = 8.0
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_parite()
kontrol("parite bozukken HATA", pf._sayac[pf.HATA] >= 1)
kontrol("gerekçe beklentinin geçersizliğini söylüyor",
        any("ÖLÇÜLMEDİ" in m for _, d, m in pf._satirlar if d == pf.HATA))
cb.FUNDING_WINDOW_HOURS = _eski

print("\n4) DEFTER YAZILAMAZSA YAKALANIYOR")
_etp = cb.TP_DEFTER_DOSYA
cb.TP_DEFTER_DOSYA = "/olmayan_dizin_xyz/tp.csv"
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_defterler()
kontrol("olmayan dizin HATA veriyor", pf._sayac[pf.HATA] >= 1)
cb.TP_DEFTER_DOSYA = _etp

print("\n5) REFERANS / RAPOR TUTARSIZLIĞI YAKALANIYOR")
import carry_rapor as cr
_ebg = cr.BEKLENEN_GUNLUK
cr.BEKLENEN_GUNLUK = 0.005          # kasten yanlış
pf._sayac.update({pf.TAMAM: 0, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
pf.kontrol_referans()
kontrol("rapor beklentisi seriden saparsa HATA", pf._sayac[pf.HATA] >= 1)
kontrol("gerekçe 'güncellenmemiş' diyor",
        any("güncellenmemiş" in m for _, d, m in pf._satirlar if d == pf.HATA))
cr.BEKLENEN_GUNLUK = _ebg

print("\n6) BELGE KODLA TUTUYOR MU (asıl madde 217 hatası)")
_ham = open(os.path.join(R, "CANLIYA_CIKIS.md"), encoding="utf-8").read()
# Belgenin BASINDAKI alinti blogu (">" satirlari) neyin DUZELTILDIGINI
# anlatmak icin eski YANLIS degerleri kasten aliyor. "artik icermiyor"
# kontrolleri bu blogu HARIC tutmali - yoksa dogru belgeyi kirmizi yapar.
_govde = "\n".join(s for s in _ham.splitlines() if not s.lstrip().startswith(">"))
belge = _ham          # "iceriyor mu" kontrolleri tam metne bakar
# bacak formulu: bakiye / (N_DILIM * N_LEGS / (GROSS * taban_pay))
_b = cb.N_DILIM * cb.N_LEGS / (cb.GROSS_EXPOSURE * cb.taban_pay())
# Belge Turkce ondalik ayirici kullanir; tam sayi ise noktasiz yazilir.
bolen = (f"{_b:.0f}" if abs(_b - round(_b)) < 1e-9
         else f"{_b:.1f}".replace(".", ","))
kontrol(f"belgedeki bacak formülü koddan doğru (bakiye/{bolen})",
        f"bakiye / {bolen}" in belge, f"(beklenen bakiye / {bolen})")
kontrol("belge GÖVDESİ eski formülü (bakiye/75) içermiyor",
        "bakiye / 75" not in _govde and "bakiye/75" not in _govde)
kontrol("belge bacak sayısını doğru yazıyor",
        f"{cb.N_LEGS}+{cb.N_LEGS} bacak" in belge)
kontrol("belge GÖVDESİ 12+12 demiyor", "12+12 bacak" not in _govde)
kontrol("belge dilim sayısını doğru yazıyor", f"{cb.N_DILIM} dilim" in belge)
_tur = int(round(cb.REBALANCE_HOURS / cb.N_DILIM))
kontrol(f"belge tur aralığını doğru yazıyor ({_tur} saat)",
        f"**{_tur} saatte bir**" in belge or f"{_tur} saatte bir" in belge)
kontrol("belge GÖVDESİ 'günde bir tur' demiyor",
        "Günde bir tur" not in _govde)
kontrol("belge funding penceresini doğru yazıyor",
        f"| **{int(cb.FUNDING_WINDOW_HOURS)}** |" in belge
        or f"**{int(cb.FUNDING_WINDOW_HOURS)}**" in belge)
kontrol("belge GÖVDESİ eski beklentiyi (+%91,8 / 2,76) taşımıyor",
        "+%91,8" not in _govde and "2,76" not in _govde)
kontrol("belge güncel beklentiyi yazıyor (+%96,8 / 3,02)",
        "+%96,8" in belge and "3,02" in belge)
# MADDE 231: alarm esikleri DUSUK PRIM rejiminin bootstrap p5/p1'ine
# gore gevsetildi. Eski test "−%16" / "−%19,5" alt-dizesine bakiyordu;
# "−%16,8" icinde "−%16" bulundugu icin BAYAT degerlerle de geciyordu.
# MADDE 233: belgedeki alarm esikleri KODDAN turetilir. Daha once
# belge −%17/−%21 yaziyordu, kod ise −%20/−%25 kullaniyordu - yani
# belge ile kodun soyledigi esikler BIRKAC MADDE boyunca farkliydi ve
# hicbir test bunu denetlemiyordu. Madde 217 belgeyi koda baglamisti
# ama bu iki sabiti kapsamiyordu.
_i = abs(cr.DUSUS_INCELE) * 100
_d = abs(cr.DUSUS_DURDUR) * 100
def _tr(x):   # 18.0 -> "18", 18.5 -> "18,5"
    return (f"{x:.0f}" if abs(x - round(x)) < 1e-9
            else f"{x:.1f}".replace(".", ","))
# "belgede bir yerde geciyor mu" KONTROLU YETMEZ: -%19 belgede baska
# bir baglamda bulunabiliyor ve test kod -0.19'a cekilse bile geciyordu.
# Esik, ALARM SATIRININ icinde aranir.
kontrol(f"belge İNCELE alarm satırı koddan doğru (−%{_tr(_i)})",
        f"düşüş **−%{_tr(_i)}'i** geçti" in belge
        or f"düşüş **−%{_tr(_i)}'yi** geçti" in belge,
        "(alarm satiri kod esigiyle uyusmuyor)")
kontrol("belge DURDUR satırı kod eşiğiyle uyuşuyor",
        f"düşüş **−%{_tr(_d)}'ü** geçti" in belge
        or f"düşüş **−%{_tr(_d)}'u** geçti" in belge)
kontrol("belge GÖVDESİ madde 175'in çürütülmüş eşiklerini taşımıyor",
        "**−%20'yi** geçti" not in _govde and "**−%25'i** geçti" not in _govde)
kontrol("belge GÖVDESİ eski alarm eşiklerini (−%17 / −%21) taşımıyor",
        "**−%17'yi** geçti" not in _govde and "**−%21'i** geçti" not in _govde)
kontrol("belge madde 232'nin etiket hatasını kayıtta tutuyor",
        "MADDE 232" in belge and "1,93 kat" in belge
        and "maskeleniyordu" in belge)
kontrol("belge funding eşiğini TABAN üzerinden tanımlıyor",
        "düşük prim tabanının" in belge and "%0,0653/gün" in belge)
kontrol("belge günlük raporun REJİM satırını duyuruyor",
        "REJİM satırı var" in belge)
kontrol("belge REJİM tablosunu taşıyor (madde 231)",
        "düşük prim" in belge and "yüksek prim" in belge
        and "+%95,0" in belge and "+%141,0" in belge)
kontrol("belge yayınlanan beklentinin HARMAN olduğunu söylüyor",
        "harman" in belge.lower() and "kasten DÜŞÜK" in belge)
kontrol("belge kenarın İKİ rejimde de var olduğunu söylüyor",
        "2,79" in belge and "3,15" in belge)
kontrol("belge GÖVDESİ eski düşüş eşiklerini alarm olarak vermiyor",
        "**−%20'yi** geçti" not in _govde and "**−%25'i** geçti" not in _govde)
kontrol("belge madde 214'ü yansıtıyor (funding gelir DEĞİL seçici)",
        "seçici" in belge and "çürüttü" in belge)
kontrol("belge yanlış preflight'tan UZAK DURMAYI söylüyor",
        "preflight.py" in belge and "carry_preflight.py" in belge
        and "ÇALIŞTIRMAYIN" in belge)
kontrol("belge madde 216 takvimini içeriyor",
        "gün 14" in belge.lower() and "%100" in belge)
kontrol("belge madde 211 korumalarını AÇMA listesinde tutuyor",
        "CARRY_POZ_MODU_KONTROL=0" in belge and "CARRY_IZOLE_KAPAT=0" in belge)
# teknik alt sinir: MIN_NOTIONAL x carpan x bolen
_asgari = cb.MIN_NOTIONAL_USD * cb.ASGARI_BACAK_CARPANI * _b
_as_str = f"{int(round(_asgari)):,}".replace(",", ".")
kontrol(f"belgedeki teknik alt sınır koddan doğru ({_as_str}$)",
        _as_str in belge, f"(beklenen {_as_str})")

print("\n6b) KOD İÇİ DOCSTRING DE KODLA TUTUYOR MU (madde 223)")
# Madde 217 sadece CANLIYA_CIKIS.md'yi kodla baglamisti. Madde 222 bacak
# sayisini 6 -> 5 cekti; N_DILIM docstring'indeki sermaye paragrafi bir
# tur boyunca "(15 x 6)" ve "~3.400$" demeye devam etti cunku hicbir test
# DOCSTRING'e bakmiyordu. Ayni tuzak, ayni ders: kimsenin denetlemedigi
# metin bayatlar.
_kaynak = open(os.path.join(R, "carry_bot.py"), encoding="utf-8").read()
_harita = open(os.path.join(R, "KAR_HARITASI.md"), encoding="utf-8").read()
_bs = (f"{_b:.0f}" if abs(_b - round(_b)) < 1e-9 else f"{_b:.1f}".replace(".", ","))
kontrol(f"N_DILIM docstring'i güncel bacak formülünü veriyor (bakiye/{_bs})",
        f"bakiye / {_bs}" in _kaynak, f"(beklenen bakiye / {_bs})")
kontrol(f"N_DILIM docstring'i güncel asgari bakiyeyi veriyor ({_as_str}$)",
        f"{_as_str}$" in _kaynak)
kontrol("N_DILIM docstring'i eski (15 x 6) formülünü ARTIK vermiyor",
        "`bakiye x 0.40 / (15 x 6)`" not in _kaynak)
kontrol("N_DILIM docstring'i eski ~3.400$ eşiğini AYAR ÖNERİSİ olarak vermiyor",
        "**3.500$\naltındaki" not in _kaynak
        and "3.500$ altındaki hesaplarda" not in _kaynak)
# docstring'deki dilim -> asgari bakiye tablosu koddan dogru mu
for _nd2, _bek in ((5, 62.5), (6, 75.0), (10, 125.0), (15, 187.5)):
    _hesap = _nd2 * cb.N_LEGS / (cb.GROSS_EXPOSURE * cb.taban_pay())
    kontrol(f"docstring tablosu N_DILIM={_nd2} için koddan doğru",
            abs(_hesap - _bek) < 1e-9
            and f"{cb.MIN_NOTIONAL_USD * cb.ASGARI_BACAK_CARPANI * _hesap:,.0f}"
                .replace(",", ".") in _kaynak,
            f"(hesap {_hesap})")
kontrol("KALABALIK_HAVUZ docstring'i madde 224 taramasını taşıyor",
        "MADDE 224" in _kaynak and "DEĞER KAYAR, ARGMAX KAYMAZ" in _kaynak)
# madde 224 tablosunda YILDIZLI satir secilen havuzdur; o satirin havuz
# degeri kodla ayni olmali (ayar degisirse bu test kirilir).
_kh = _kaynak.split("KALABALIK_HAVUZ = ", 1)[1].split('"""')[1]
_yildizli = [s for s in _kh.splitlines()
             if s.count("*") >= 4 and s.strip() and s.strip()[0].isdigit()]
kontrol("madde 224 tablosunda yıldızlı satır = koddaki KALABALIK_HAVUZ",
        len(_yildizli) == 1
        and abs(float(_yildizli[0].split()[0]) - cb.KALABALIK_HAVUZ) < 1e-9,
        f"({_yildizli})")
kontrol("madde 224 YANLIŞ ÇIKAN tahmini kayıtta tutuyor (dürüstlük)",
        "YANLIŞ ÇIKAN TAHMİN" in _kaynak and "etkileşim yok" in _kaynak)
kontrol("REBALANCE_HOURS docstring'i madde 223 taramasını taşıyor",
        "MADDE 223" in _kaynak and "eşit-risk" in _kaynak
        and str(int(cb.REBALANCE_HOURS / 24)) + " gün" in _kaynak)
import karar_kurali as _kk
kontrol("karar_kurali şart 3'ün VETO olduğunu yazıyor (madde 223)",
        "VETO" in _kk.__doc__ and "kabul gerekçesi DEĞİL" in _kk.__doc__)
kontrol("karar_kurali DÖRT şart sayıyor (madde 225)",
        "DÖRT ŞART" in _kk.__doc__ and "KALDIRAÇ GEREKMESİN" in _kk.__doc__)
kontrol("REZERV_PAY docstring'i madde 225 taramasını ve 4. şartı taşıyor",
        "MADDE 225" in _kaynak and "NAKİT" in _kaynak
        and "KALDIRAÇ kararıdır" in _kaynak)
import carry_rapor as _cr2
kontrol("carry_rapor beklentinin REJİM HARMANI olduğunu yazıyor (madde 231)",
        "MADDE 231" in _cr2.__doc__ or "MADDE 231" in open(
            os.path.join(R, "carry_rapor.py"), encoding="utf-8").read())
_rk = open(os.path.join(R, "carry_rapor.py"), encoding="utf-8").read()
kontrol("rapor üç rejimin sayılarını taşıyor",
        "+112.5%" in _rk and "+95.0%" in _rk and "+141.0%" in _rk)
kontrol("rapor eski alarm eşiklerinin NEDEN gevşetildiğini yazıyor",
        "-%22,3" in _rk and "YANLIŞ ALARM" in _rk)
_nl = _kaynak.split("N_LEGS = ", 1)[1].split('"""')[1]
kontrol("N_LEGS docstring'i madde 230'u (iki taraf asimetrisi) taşıyor",
        "MADDE 230" in _nl and "16 KAT sönüm" in _nl
        and "standart funding oranında" in _nl)
kontrol("madde 230 eşit-risk gerçeğini yazıyor (başlık kaldıraçtı)",
        "tamamen" in _nl and "KALDIRAÇ" in _nl and "5,4 puan" in _nl)
kontrol("madde 230 YANLIŞ çıkan mekanizmayı kayıtta tutuyor",
        "MEKANİZMA DÜZELTMESİ" in _nl and "kalabalık" in _nl)
_uc = _kaynak.split("UC_HAREKET_ELE = ", 1)[1].split('"""')[1]
kontrol("UC_HAREKET_ELE docstring'i madde 236 taramasını taşıyor",
        "MADDE 236" in _uc and "TEK YÖNLÜ DEĞİL" in _uc)
kontrol("madde 236 KUYRUK/ZARAR seçici ayrımını yazıyor",
        "KUYRUK seçicisi" in _uc and "İKİ KUYRUKTA DA" in _uc)
kontrol("madde 236 nitelik tablosunu (iki kuyruk) taşıyor",
        "+0,0669" in _uc and "+0,0699" in _uc and "%100" in _uc)
kontrol("madde 236 seçilen eşiği koddan doğru yazıyor",
        f"{cb.UC_HAREKET_ELE:.2f}".replace(".", ",") in _uc)
kontrol("KAR_AL docstring'i madde 235 çıkış-şekli ailesini taşıyor",
        "MADDE 235" in _kaynak and "kılık değiştirmiş bir" in _kaynak
        and "en iyi takip, takip olmamasıdır" in _kaynak)
kontrol("madde 235 merdivenin REDDEDİLDİĞİNİ ve sebebini yazıyor",
        "KABUL EDİLMEDİ" in _kaynak and "%93,9" in _kaynak
        and "yazı-tura" in _kaynak)
kontrol("madde 235 bütçe ölçümünü (değme oranları) taşıyor",
        "%42,9" in _kaynak and "%21,4" in _kaynak and "32.250" in _kaynak)
_ka0 = _kaynak.split("KAR_AL_ORAN = ", 1)[1].split('"""')[1]
kontrol("KAR_AL docstring'i madde 229'u (boş koltuk YASASI) taşıyor",
        "MADDE 229" in _ka0 and "%5,01" in _ka0 and "11,4 puan" in _ka0)
kontrol("madde 229 yasanın İKİ bağımsız ölçümünü adlandırıyor",
        "madde 225" in _ka0 and "madde 229" in _ka0)
_ak = _kaynak.split("AKIS_AGIRLIK = ", 1)[1].split('"""')[1]
kontrol("AKIS_AGIRLIK docstring'i madde 228'i ve YÜK TAŞIMIYOR sonucunu taşıyor",
        "MADDE 228" in _ak and "YÜK TAŞIMIYOR" in _ak and "%90" in _ak)
kontrol("AKIS docstring'i kapatmanın GERÇEK bedelini yazıyor (~2,9 puan)",
        "2,9 puan" in _ak)
_yg = _kaynak.split("MIN_LISTELEME_GUN = ", 1)[1].split('"""')[1]
kontrol("MIN_LISTELEME_GUN docstring'i madde 228'i taşıyor",
        "MADDE 228" in _yg and "yanlış gerekçeyle" in _yg)
kontrol("yaş docstring'i seçilen eşiği koddan doğru yazıyor",
        f"{cb.MIN_LISTELEME_GUN} gün" in _yg)
_ka = _kaynak.split("KAR_AL_ORAN = ", 1)[1].split('"""')[1]
kontrol("KAR_AL_ORAN docstring'i madde 227 taramasını taşıyor",
        "MADDE 227" in _ka and "TEK BİR GERÇEKLEŞMENİN" in _ka)
kontrol("KAR_AL docstring'i seçilen iki eşiği koddan doğru yazıyor",
        f"{cb.KAR_AL_ORAN:.2f}".replace(".", ",") in _ka
        and f"{cb.KAR_AL_SHORT:.2f}".replace(".", ",") in _ka)
kontrol("madde 227 listenin EKSİK olduğunu kayıtta tutuyor (dürüstlük)",
        "listenin kendisi eksikti" in _ka.lower()
        or "listesine hiç GİRMEDİ" in _ka)
kontrol("MIN_DAILY_VOLUME_USD docstring'i madde 226 taramasını taşıyor",
        "MADDE 226" in _kaynak and "her iki yandan" in _kaynak
        and "15" in _kaynak.split("MIN_DAILY_VOLUME_USD = ", 1)[1].split('"""')[1])
kontrol("MIN_DAILY_VOLUME_USD docstring'i seçilen eşiği koddan doğru yazıyor",
        f"{int(cb.MIN_DAILY_VOLUME_USD/1e6)}M" in
        _kaynak.split("MIN_DAILY_VOLUME_USD = ", 1)[1].split('"""')[1])
kontrol("REZERV_PAY docstring'i seçilen değeri koddan doğru yazıyor",
        f"{cb.REZERV_PAY:.2f}" in _kaynak.split("REZERV_PAY = ", 1)[1].split('"""')[1])

_k238 = _kaynak.split("KAR_AL_ORAN = ", 1)[1].split('"""')[1]
kontrol("KAR_AL docstring'i madde 238 katman merdivenini taşıyor",
        "MADDE 238" in _k238 and "+72.5%" in _k238 and "+26.1%" in _k238)
kontrol("madde 238 çıplak seçicinin düşüşünü ve tam kitabı birlikte yazıyor",
        "−34.8" in _k238 and "+112.5%" in _k238 and "2.942" in _k238)
kontrol("madde 238 TOPLAMSAL DEĞİL dersini yazıyor",
        "TOPLAMSAL DEĞİL" in _k238 and "madde 228/236" in _k238)
_kt = __import__("arastirma_katman")
kontrol("arastirma_katman.py altı katmanı da taşıyor",
        len(_kt.KATMANLAR) == 6 and len(_kt.OLCUM) == 6
        and all(h in _kt.OLCUM for _, h in _kt.KATMANLAR))
kontrol("araç ile docstring aynı çıplak/tam kitap rakamını söylüyor",
        _kt.OLCUM["A_CIPLAK"] == (72.5, 1.389, -34.8, 26.1)
        and _kt.OLCUM["F_TAM"] == (112.5, 2.942, -14.5, 112.5))
kontrol("madde 238: tam kitabın eşit-riski kendi getirisine eşit (referans satır)",
        _kt.OLCUM["F_TAM"][0] == _kt.OLCUM["F_TAM"][3])
kontrol("madde 238: en büyük iki katman KÂR AL ve kalabalık havuzu",
        round(_kt.OLCUM["F_TAM"][3] - _kt.OLCUM["E_REZERV"][3], 1) == 50.7
        and round(_kt.OLCUM["B_HAVUZ"][3] - _kt.OLCUM["A_CIPLAK"][3], 1) == 42.8)

_g239 = _kaynak.split("GROSS_EXPOSURE = ", 1)[1].split('"""')[1]
kontrol("GROSS_EXPOSURE docstring'i madde 239 prim bütçesini taşıyor",
        "MADDE 239" in _g239 and "+%239,9" in _g239 and "DÜZ" in _g239)
kontrol("madde 239 reddi ŞART 1'e bağlıyor ve kuralın değişmediğini yazıyor",
        "ŞART 1" in _g239 and "%95,6" in _g239 and "%48,2" in _g239
        and "DEĞİŞTİRİLMEDİ" in _g239)
kontrol("madde 239 plaseboyu ve 'doz değil zamanlama'yı yazıyor",
        "PLASEBO" in _g239 and "+%92,5" in _g239 and "ZAMANLAMA" in _g239)
kontrol("madde 239 KALDIRAÇ uyarısını ve likidasyon notunu taşıyor",
        "KALDIRAÇ" in _g239 and "likidasyonu modellemez" in _g239)
_r239 = _kaynak.split("REBALANCE_HOURS = ", 1)[1].split('"""')[1]
kontrol("REBALANCE_HOURS docstring'i madde 239 vade merdivenini taşıyor",
        "MADDE 239" in _r239 and "+3,9 puan" in _r239 and "%59,7" in _r239)
kontrol("madde 239 merdiven yan bulgusunu (+0,875 korelasyon) yazıyor",
        "+0,875" in _r239 and "+0,718" in _r239)
_pb = __import__("arastirma_prim_butce")
kontrol("prim bütçesi aracı dört çeyreği de taşıyor ve TEK YÖNLÜ",
        len(_pb.CEYREK_TAM) == 4
        and [v[0] for v in _pb.CEYREK_TAM.values()]
        == sorted(v[0] for v in _pb.CEYREK_TAM.values()))
kontrol("prim ölçüsü NEDENSEL: yerel referans penceresi ölçümden uzun",
        _pb.REFERANS_GUN > _pb.OLCUM_GUN and _pb.REFERANS_GUN == 180)
kontrol("prim bütçesi 2025-26'da TEK YÖNLÜ OLMADIĞINI kayıtta tutuyor",
        [v[0] for v in _pb.CEYREK_2526.values()]
        != sorted(v[0] for v in _pb.CEYREK_2526.values()))
_pk = __import__("arastirma_prim_karar")
kontrol("prim karar aracı: plasebo eşit riskte kontrolün ALTINDA",
        _pk.ADAYLAR["PLASEBO ters"][5] < _pk.KONTROL[5])
kontrol("prim karar aracı: seçilen varyant kontrolü GEÇİYOR ama ort brüt > 1",
        _pk.ADAYLAR["e0.5 ref180"][5] > _pk.KONTROL[5]
        and _pk.ADAYLAR["e0.5 ref180"][6] > 1.0)
kontrol("prim karar aracı: alt dönem bootstrap 22-24'te güçlü, 25-26'da yazı-tura",
        _pk.ALT_DONEM["22-24"][3] > 90.0 and 40.0 < _pk.ALT_DONEM["25-26"][3] < 60.0)
kontrol("prim karar aracı: yalnız nakde çekme kazanç VERMİYOR (<5 puan)",
        _pk.ADAYLAR["ust1.0 (nakit)"][5] - _pk.KONTROL[5] < 5.0)
_vm = __import__("arastirma_vade_merdiveni")
kontrol("vade merdiveni: tam örnek kazancı bootstrap'ta ÇÖKÜYOR",
        _vm.HARMAN[0.25][5] - 112.2 > 15.0 and _vm.BOOTSTRAP[0.25][2] < 6.0)
kontrol("vade merdiveni: doz-yanıt TERS (2g payı arttıkça güven azalıyor)",
        _vm.BOOTSTRAP[0.25][1] > _vm.BOOTSTRAP[0.50][1] > _vm.BOOTSTRAP[1.00][1])
kontrol("vade merdiveni: 2g-5g korelasyonu momentumun 0,718'inden YÜKSEK",
        _vm.KORELASYON[(2, 5)] > 0.718)

_df = __import__("arastirma_yeniden_acma_defteri")
_son, _atifsiz = _df.defter("carry_bot.py")
kontrol("yeniden açma defteri parametreleri koddan okuyor (>40 parametre)",
        len(_son) + len(_atifsiz) > 40)
kontrol("DEFTER DENETİMİ BOŞ: madde 222 öncesi hesapsız parametre yok",
        _df.denetim("carry_bot.py") == [])
kontrol("madde 240'ta açılan dört parametre defterde 240 görünüyor",
        all(_son.get(a) == 240 for a in ("FUNDING_WINDOW_HOURS",
            "REZERV_ESIK_YILLIK", "REZERV_COIN_KAP", "DONUK_ESIK")))
kontrol("KAPALI_EKSEN gerekçeleri bir MADDEYE atıf yapıyor (kanaat değil)",
        all(_df.MADDE.search(v) for v in _df.KAPALI_EKSEN.values()))
kontrol("LEVERAGE defterde kapalı eksende ve BEKLEYEN karar olarak yazılı",
        "227" in _df.KAPALI_EKSEN["LEVERAGE"]
        and "BEKLEYEN" in _df.KAPALI_EKSEN["LEVERAGE"].upper())
_m240 = __import__("arastirma_madde240")
kontrol("madde 240: pencere ekseni TEK YÖNLÜ ve tepe 48 saatte",
        max(_m240.PENCERE, key=lambda k: _m240.PENCERE[k][1]) == "48 saat")
kontrol("madde 240: pencere tepesi SİVRİ (komşulardan >=0,06 Sharpe üstün)",
        _m240.PENCERE["48 saat"][1] - _m240.PENCERE["60 saat"][1] >= 0.06
        and _m240.PENCERE["48 saat"][1] - _m240.PENCERE["36 saat"][1] >= 0.10)
kontrol("madde 240: rezerv eşiği ekseni eşit riskte DÜZ (yayılım <= 3 puan)",
        max(v[5] for v in _m240.REZERV_ESIK.values())
        - min(v[5] for v in _m240.REZERV_ESIK.values()) <= 3.0)
kontrol("madde 240: rezerv eşiğinde getiri tek yönlü DÜŞÜYOR",
        [_m240.REZERV_ESIK[k][0] for k in ("%1,0", "%1,2", "%1,5", "%1,8",
         "%2,0", "%2,2", "%2,5", "%3,0")]
        == sorted((v[0] for v in _m240.REZERV_ESIK.values()), reverse=True))
kontrol("madde 240: coin kapısı DOZ dial'i - getiri VE düşüş birlikte artıyor",
        _m240.REZERV_KAP["%15"][0] > _m240.REZERV_KAP["%5"][0]
        and _m240.REZERV_KAP["%15"][4] > _m240.REZERV_KAP["%5"][4])
kontrol("madde 240: donuk eşiği sıkılaştırmak eşit riskte kaybettiriyor",
        _m240.DONUK["0,20"][5] < _m240.DONUK["0,10"][5]
        and _m240.DONUK["0,30"][5] < _m240.DONUK["0,20"][5])
_fw = _kaynak.split("FUNDING_WINDOW_HOURS = ", 1)[1].split('"""')[1]
kontrol("FUNDING_WINDOW docstring'i madde 240'ı ve 'keskinleşti'yi yazıyor",
        "MADDE 240" in _fw and "keskinleşti" in _fw and "0,069" in _fw)
_re_ = _kaynak.split("REZERV_ESIK_YILLIK = ", 1)[1].split('"""')[1]
kontrol("REZERV_ESIK docstring'i madde 240'ı ve PÜRÜZSÜZLÜK dersini yazıyor",
        "MADDE 240" in _re_ and "pürüzsüzlük" in _re_ and "+0,3 puan" in _re_)
_rk = _kaynak.split("REZERV_COIN_KAP = ", 1)[1].split('"""')[1]
kontrol("REZERV_COIN_KAP docstring'i madde 240'ı ve DOZ dersini yazıyor",
        "MADDE 240" in _rk and "doz" in _rk.lower())
_de = _kaynak.split("DONUK_ESIK = ", 1)[1].split('"""')[1]
kontrol("DONUK_ESIK docstring'i madde 240'ı taşıyor",
        "MADDE 240" in _de and "0,10 TEPEDE" in _de)
_ks = _kaynak.split("KAR_AL_SHORT = ", 1)[1].split('"""')[1]
kontrol("KAR_AL_SHORT çapraz atfı var (defterin yapısal sınırı)",
        "MADDE 227" in _ks and "MADDE 240" in _ks)

_ok = __import__("arastirma_olay_kolu")
kontrol("madde 241: pump->SHORT kazanma oranı yüksek AMA ortalama medyanın çok altında",
        _ok.OLAY["pump -> SHORT"][3] > 60.0
        and _ok.OLAY["pump -> SHORT"][1] < _ok.OLAY["pump -> SHORT"][2] / 2)
kontrol("madde 241: kuyruk kayıtta (p1 ve en kötü işlem)",
        _ok.OLAY["pump -> SHORT"][4] < -100.0
        and _ok.OLAY["pump -> SHORT"][5] < -500.0)
kontrol("madde 241: dump tarafının ARZI yok (eşik yükseldikçe dumpsız gün artar)",
        [_ok.ARZ[e][2] for e in (0.20, 0.30, 0.40, 0.50)]
        == sorted(_ok.ARZ[e][2] for e in (0.20, 0.30, 0.40, 0.50))
        and _ok.ARZ[0.40][2] >= 85)
kontrol("madde 241: ±%40'ta dump arzı pump'ın beşte birinden az",
        _ok.ARZ[0.40][1] < _ok.ARZ[0.40][0] / 4)
kontrol("madde 241: 03:00 (00 UTC) en iyi saat DEĞİL",
        _ok.SAAT["04 UTC = 07:00 Ist."][1] > _ok.SAAT["00 UTC = 03:00 Ist."][1])
kontrol("madde 241: her saat varyantı 2022-24'te NEGATİF",
        all(v[2] < 0 for v in _ok.SAAT.values()))
kontrol("madde 241: olay kolu eşit riskte HER payda kaybettiriyor",
        all(_ok.PAY_OLAY[w][5] < _ok.PAY_OLAY[0.00][5] for w in (0.05, 0.10, 0.20)))
kontrol("madde 241: %5'te Sharpe YÜKSELİYOR ama eşit-risk DÜŞÜYOR (sınırın kanıtı)",
        _ok.PAY_OLAY[0.05][1] > _ok.PAY_OLAY[0.00][1]
        and _ok.PAY_OLAY[0.05][5] < _ok.PAY_OLAY[0.00][5])
kontrol("madde 241: geri dönüş payı TEK YÖNLÜ kötü",
        [_ok.PAY_GERIDONUS[w][3] for w in (0.00, 0.05, 0.10, 0.15, 0.25, 0.50, 1.00)]
        == sorted((_ok.PAY_GERIDONUS[w][3] for w in _ok.PAY_GERIDONUS), reverse=True))
kontrol("madde 241: eleme eşitsizliği dört ölçümde de işareti doğru veriyor",
        all((s > _ok.gereken(k)) == (g == "YUKSELDI")
            for s, k, g in _ok.ESITSIZLIK.values()))
kontrol("madde 241: geri dönüş korelasyonu momentumdan DÜŞÜK (eleyen korelasyon değil)",
        _ok.ESITSIZLIK["geri donus (241)"][1]
        < _ok.ESITSIZLIK["momentum (237)"][1])
_uh = _kaynak.split("UC_HAREKET_ELE = ", 1)[1].split('"""')[1]
kontrol("UC_HAREKET_ELE docstring'i madde 241'i ve opsiyon SATMAK dersini taşıyor",
        "MADDE 241" in _uh and "SATMAK" in _uh and "%68,6" in _uh)
kontrol("KÂR HARİTASI C3'ü artık kapalı formu taşıyor (madde 241)",
        "Sh_kol > Sh_ana × korelasyon" in _harita
        and "ELEME** aracıdır" in _harita)

_fk = __import__("arastirma_faktoriyel")
kontrol("madde 242: faktöriyel 16 hücrenin tamamını taşıyor",
        len(_fk.HUCRE) == 16 and "MERKEZ" in _fk.HUCRE)
kontrol("madde 242: MERKEZ Sharpe'ta 1/16, eşit-riskte 16/16",
        _fk.siralama("sharpe") == 1 and _fk.siralama("esit") == 16)
kontrol("madde 242: alternatif hücrelerin HEPSİ eşit-riski merkezin ÜSTÜNDE gösteriyor",
        all(t[6] > _fk.HUCRE["MERKEZ"][6]
            for a, t in _fk.HUCRE.items() if a != "MERKEZ"))
kontrol("madde 242: alternatif hücrelerin HEPSİ Sharpe'ı merkezin ALTINDA",
        all(t[2] < _fk.HUCRE["MERKEZ"][2]
            for a, t in _fk.HUCRE.items() if a != "MERKEZ"))
kontrol("madde 242: kaldıraçsız kalan tek hücre MERKEZ",
        sum(1 for t in _fk.HUCRE.values() if t[7] <= 1.005) == 1
        and _fk.HUCRE["MERKEZ"][7] <= 1.005)
kontrol("madde 242: etkileşimler ana etkilerin yanında İHMAL EDİLEBİLİR (<%15)",
        max(abs(v[0]) for v in _fk.ETKILESIM.values())
        < 0.15 * max(abs(v[0]) for v in _fk.ANA_ETKI.values()))
kontrol("madde 242: en uzak köşenin tam örnek kazancı bootstrap'ta İŞARET DEĞİŞTİRİYOR",
        _fk.HUCRE["TP0.50 H4 U0.60 R0.30"][6] > _fk.HUCRE["MERKEZ"][6]
        and _fk.BOOTSTRAP["en uzak kose (4 dgs)"][2] < 0)
kontrol("madde 242: TP0,50 bootstrap'ı madde 227'yi tekrarlıyor (P %60-70 bandı)",
        60.0 < _fk.BOOTSTRAP["TP0,50 tek (1 dgs)"][3] < 70.0)
_kk = open(os.path.join(R, "karar_kurali.py"), encoding="utf-8").read()
kontrol("karar kuralı docstring'i madde 242'yi ve 1/16 - 16/16 bulgusunu taşıyor",
        "MADDE 242" in _kk and "1/16" in _kk and "16/16" in _kk)
kontrol("KÂR HARİTASI madde 242'nin toplamsallık bulgusunu taşıyor",
        "MADDE 242" in _harita and "+0,004" in _harita)

_ra = __import__("arastirma_risk_atfi")
kontrol("madde 243: BTC betası sıfırdan ayırt edilemez (|t| < 2)",
        abs(_ra.FAKTOR["BTC"][1][0][2]) < 2.0
        and _ra.FAKTOR["BTC"][0] < 0.001)
kontrol("madde 243: bulunan tek maruziyet İSTATİSTİKSEL olarak gerçek (|t| > 3)",
        abs(_ra.FAKTOR["BTC + (ALT-BTC)"][1][1][2]) > 3.0)
kontrol("madde 243: o maruziyeti hedge etmek TEK YÖNLÜ kötü",
        [_ra.HEDGE[b][5] for b in (0.0, 0.053, 0.10, 0.25)]
        == sorted((v[5] for v in _ra.HEDGE.values()), reverse=True))
kontrol("madde 243: hedge düşüşü de KÖTÜLEŞTİRİYOR (sızıntı değil gelir)",
        _ra.HEDGE[0.053][4] < _ra.HEDGE[0.000][4])
kontrol("madde 243: varyans oranlarının HEPSİ 1'in altında (kümelenme yok)",
        all(v < 1.0 for v in _ra.VARYANS_ORANI.values()))
kontrol("madde 243: gerçek düşüş karıştırılmıştan SIĞ (yüzdelik > %70)",
        _ra.KARISTIRMA["yuzdelik"] > 70.0
        and _ra.KARISTIRMA["gercek"] > _ra.KARISTIRMA["p50"])
kontrol("madde 243: ileriye dönük 1 yıl p5'i gerçekleşenden DERİN",
        _ra.BIR_YIL["karistirilmis"][2] < _ra.BIR_YIL["gercek"][2])
kontrol("madde 243: alarm yanlış tetikleme DURDUR'da %5'in altında",
        _ra.YANLIS_TETIK["DURDUR -%23"][1] < 5.0)
kontrol("madde 243: İNCELE eşiği DURDUR'dan daha sık tetikliyor (sıralama tutarlı)",
        _ra.YANLIS_TETIK["INCELE -%18"][1] > _ra.YANLIS_TETIK["DURDUR -%23"][1])
_cr2 = open(os.path.join(R, "carry_rapor.py"), encoding="utf-8").read()
kontrol("DUSUS_INCELE docstring'i madde 243'ün yanlış tetikleme sayılarını taşıyor",
        "MADDE 243" in _cr2 and "%11,1" in _cr2 and "%2,2" in _cr2)
kontrol("DUSUS_INCELE docstring'i ileriye dönük p5'i (−%20,55) yazıyor",
        "20,55" in _cr2 and "ŞANSLI SIRALAMA" in _cr2)
kontrol("KÂR HARİTASI E3 yol-müdahalesi ailesinin sebebini taşıyor",
        "YOL DÜZEYİNDE MÜDAHALE EDİLEMEZ" in _harita and "%84" in _harita)
kontrol("CANLIYA_CIKIS madde 243'ün dürüst düşüş beklentisini taşıyor",
        "MADDE 243" in _ham and "−%20,6 / −%25,3" in _ham
        and "şanslı bir sıralama" in _ham)
kontrol("belgedeki sıralama-testi p5'i araçla AYNI (koddan denetlenir)",
        f"{abs(_ra.BIR_YIL['karistirilmis'][2]):.1f}".replace(".", ",") in _ham)

_as = __import__("arastirma_alternatif_strateji")
kontrol("madde 244: carry sinyalinin fiyat IC'si sıfırdan ayırt edilemez",
        abs(_as.IC["carry (kitabin sinyali)"][1]) < 2.0)
kontrol("madde 244: IC EN GÜÇLÜ iki sinyal kitapta EN KÖTÜ Sharpe'ı veriyor",
        _as.TEK_BASINA["ust trader IZLE"][1] < _as.TEK_BASINA["ust trader KONTRARIAN"][1]
        and _as.TEK_BASINA["kalabalik IZLE"][1] < _as.TEK_BASINA["kalabalik KONTRARIAN"][1])
kontrol("madde 244: IC işareti ile kitap sıralaması TERS (ölçülen hedef yanlış)",
        _as.IC["ust trader IZLE"][0] > 0 > -_as.IC["ust trader IZLE"][0]
        and _as.TEK_BASINA["ust trader KONTRARIAN"][1]
        - _as.TEK_BASINA["ust trader IZLE"][1] > 1.0)
kontrol("madde 244: üst trader kontrarian eşitsizliği GEÇİYOR",
        _as.esitsizlik("ust trader KONTRARIAN")[1] is True)
kontrol("madde 244: marj projenin en genişi (>0,25) ama yine de kabul edilmedi",
        _as.TEK_BASINA["ust trader KONTRARIAN"][1]
        - _as.esitsizlik("ust trader KONTRARIAN")[0] > 0.25)
kontrol("madde 244: kol SHARPE'ı yükseltiyor ama KALDIRAÇ gerektiriyor",
        _as.PAY[0.20][1] > _as.PAY[0.00][1] and _as.PAY[0.20][6] > 1.005)
kontrol("madde 244: kol kaldıraçsız ÜSTÜN DEĞİL (getirisi kontrolden az)",
        _as.PAY[0.20][0] < _as.PAY[0.00][0])
kontrol("madde 244: tam örnek kazancı bootstrap'ta YARIYA düşüyor",
        _as.BOOTSTRAP[0.20][2] < (_as.PAY[0.20][5] - _as.PAY[0.00][5]) / 1.5
        and _as.BOOTSTRAP[0.20][3] < 70.0)
kontrol("madde 244: prim harmanı TEK YÖNLÜ kontrolün altında",
        all(v[1] < _as.SH_ANA for v in _as.HARMAN_PRIM.values()))
kontrol("madde 244: prim korelasyonu 0,9'un üstünde (aynı sinyalin ölçümü)",
        _as.TEK_BASINA["prim 48sa"][5] > 0.90)
kontrol("madde 244: MOTOR/GÜNLÜK Sharpe karışıklığı kayıt altında (3. tekrar)",
        "2,84" in _as.__doc__ and "2,676" in _as.__doc__
        and "madde 223 ve 237" in _as.__doc__)
kontrol("KÂR HARİTASI C3 artık 'IC ile elemeyin' kuralını taşıyor",
        "IC ile elemeyin" in _harita and "MADDE 244" in _harita)

_dz = __import__("arastirma_doz_siniri")
kontrol("madde 245: doz cetveli brütle DOĞRUSAL (Sharpe sabit, borç maliyeti yok)",
        all(_dz.CETVEL[g][0] > _dz.CETVEL[h][0]
            for g, h in zip((1.25, 1.5, 2.0, 2.5, 3.0), (1.0, 1.25, 1.5, 2.0, 2.5))))
kontrol("madde 245: düşüş de brütle büyüyor (bedava getiri yok)",
        all(_dz.CETVEL[g][1] < _dz.CETVEL[h][1]
            for g, h in zip((1.25, 1.5, 2.0, 2.5, 3.0), (1.0, 1.25, 1.5, 2.0, 2.5))))
kontrol("madde 245: 1 yıl p1 düşüşü maks düşüşten DAHA DERİN (madde 243 tutarlı)",
        all(t[4] < t[1] for t in _dz.CETVEL.values()))
kontrol("madde 245: likidasyon güvenlik çarpanı brütle AZALIYOR",
        [_dz.LIKIDASYON[g][2] for g in (1.0, 1.5, 2.0, 3.0, 5.0, 8.0)]
        == sorted((v[2] for v in _dz.LIKIDASYON.values()), reverse=True))
kontrol("madde 245: brüt 3x'te güvenlik çarpanı 5'in ÜSTÜNDE (bağlayıcı değil)",
        _dz.LIKIDASYON[3.0][2] > 5.0)
kontrol("madde 245: brüt 8x'te çarpan 3'e DÜŞÜYOR (sınır kayıtta)",
        _dz.LIKIDASYON[8.0][2] < 3.5)
kontrol("madde 245: en kötü bacak, en kötü GÜNÜN yarısından AZ",
        abs(_dz.BACAK["en kotu"]) < _dz.EN_KOTU_GUN / 2)
kontrol("madde 245: defter ölçeği muhasebe özdeşliğiyle doğrulandı (<%5 fark)",
        _dz.OZDESLIK["bagil fark %"] < 5.0)
kontrol("madde 245: şart 4 kuralı DEĞİŞTİRİLMEDİ, revizyon ADAYI olarak yazıldı",
        "DEGISTIRILMEDI" in _dz.__doc__ and "GOZDEN GECIRME" in _dz.__doc__)
kontrol("KÂR HARİTASI doz satırı madde 245'in cetvelini taşıyor",
        "+%675,3" in _harita and "MADDE 245" in _harita)

_fa = __import__("arastirma_funding_araligi")
kontrol("madde 246: evrenin YARISINDAN FAZLASI 4 saatlik ödüyor",
        _fa.ARALIK_DAGILIMI[4] > sum(_fa.ARALIK_DAGILIMI.values()) / 2)
kontrol("madde 246: aralık geçişi gözlenmedi (sabit yapı)",
        _fa.ARALIK_DEGISEN == 0)
kontrol("madde 246: her çeyrekte 4 saatlikler DAHA ÇOK funding veriyor",
        all(f > 0 for _, _, f in _fa.SAPMA.values()))
kontrol("madde 246: ODE/sinyal sapması %15'in üstünde (gerçek sapma)",
        _fa.ODE_SINYAL_ORANI[4] / _fa.ODE_SINYAL_ORANI[8] > 1.15)
kontrol("madde 246: KONTROL üç düzeltmenin HEPSİNİ eşit riskte geçiyor",
        all(_fa.VARYANT["KONTROL (medyan + 4sa taban)"][5] > t[5]
            for a, t in _fa.VARYANT.items() if not a.startswith("KONTROL")))
kontrol("madde 246: düzeltmelerin HEPSİ düşüşü DERİNLEŞTİRİYOR (tazminat kanıtı)",
        all(t[4] < _fa.VARYANT["KONTROL (medyan + 4sa taban)"][4]
            for a, t in _fa.VARYANT.items() if not a.startswith("KONTROL")))
kontrol("madde 246: aralığı yoksaymanın bedeli 50 puandan BÜYÜK",
        _fa.ARALIGI_YOKSAYMANIN_BEDELI > 50.0)
kontrol("madde 246: ODE penceresi 48 saatte tepe yapıyor",
        max(_fa.PENCERE, key=_fa.PENCERE.get) == 48)
kontrol("madde 246: hata kaydı (hipotez çürütüldü) docstring'de",
        "HATA KAYDI" in _fa.__doc__ and "CURUTTU" in _fa.__doc__)
kontrol("KÂR HARİTASI uç-yasasına madde 246'nın SINIRINI yazdı",
        "MADDE 246 BU YASAYA BİR SINIR KOYDU" in _harita
        and "54,3 puan" in _harita)

_ca = __import__("arastirma_canli_ayrisma")
kontrol("madde 247: TAM CANLI yapılandırma kontrolden ayırt edilemez (|Δ| küçük)",
        abs(_ca.fark()[0]) < 3.0 and abs(_ca.fark()[1]) < 0.05
        and abs(_ca.fark()[3]) < 5.0)
kontrol("madde 247: delist ufku (canlı 30 gün) kontrolü AŞAĞI çekmiyor",
        _ca.OLCUM["delist ufku 30 (CANLI)"][5]
        >= _ca.OLCUM[_ca.KONTROL][5])
kontrol("madde 247: delist ufku her değerde kontrolle beraber (maliyet yok)",
        all(_ca.OLCUM[a][5] > _ca.OLCUM[_ca.KONTROL][5] - 1.0
            for a in ("delist ufku 15 gun", "delist ufku 30 (CANLI)",
                      "delist ufku 60 gun")))
kontrol("madde 247: işlem toleransı %25 ile %50 pratikte AYNI",
        abs(_ca.OLCUM["islem toleransi %25"][5]
            - _ca.OLCUM["islem tol. %50 (CANLI)"][5]) < 1.0)
kontrol("madde 247: son ölçümden 60 turdan fazla geçmişti (bayatlık kaydı)",
        _ca.BU_MADDE - _ca.ONCEKI_OLCUM_MADDE > 60)
_df2 = __import__("arastirma_yeniden_acma_defteri")
kontrol("defterdeki iki gerekçe artık madde 247'ye atıf yapıyor",
        "247" in _df2.KAPALI_EKSEN["DELIST_UFUK_GUN"]
        and "247" in _df2.KAPALI_EKSEN["ISLEM_TOLERANSI"])

_ks = __import__("arastirma_kural_sicili")
kontrol("madde 248: şart 4 TEK BAŞINA hiçbir adayı engellemedi",
        _ks.sart4_belirleyici_mi() == [])
kontrol("madde 248: sicildeki adayların ÇOĞU şart 1'den düşüyor",
        sum(1 for _, s_ in _ks.SICIL.values() if s_ == "iki donemde Sharpe")
        > len(_ks.SICIL) / 2)
kontrol("madde 248: iki alt dönemin farkları BAĞIMSIZ (|kor| < 0,1)",
        abs(_ks.KORELASYON) < 0.1)
kontrol("madde 248: şart 1'in yanlış red oranı %70'in üstünde",
        _ks.YANLIS_RED > 70.0)
kontrol("madde 248: ölçülen geçme oranı analitik %25'e yakın (±%8)",
        abs(_ks.SART1_GECME - 25.0) < 8.0)
kontrol("madde 248: sekiz EŞDEĞER plasebonun HİÇBİRİ şart 1'i geçmedi",
        sum(1 for v in _ks.PLASEBO.values() if v[4]) == 0
        and len(_ks.PLASEBO) == 8)
kontrol("madde 248: bootstrap da adayları ayırt edilemez buldu (hepsi P<%80)",
        all(p < 80.0 for _, p in _ks.BOOTSTRAP_SICILI.values()))
kontrol("madde 248: iki hata kaydı (şart-4 önerisi + FAZ_KAY plasebosu) yazılı",
        "BU YANLISTI" in _ks.__doc__ and "MODULO AYNI" in _ks.__doc__)
_kk2 = open(os.path.join(R, "karar_kurali.py"), encoding="utf-8").read()
kontrol("karar kuralı docstring'i madde 248'in yanlış red oranını taşıyor",
        "MADDE 248" in _kk2 and "%22,2" in _kk2
        and "GÖSTERİLEMEDİ" in _kk2)

import arastirma_ikinci_borsa as _ib
kontrol("madde 249: backtester TP KAPALI hâlde motorun A satırını üretiyor",
        abs(_ib.DOGRULAMA["TP yok  bt()"][0]
            - _ib.DOGRULAMA["TP yok  motor (madde 238 A)"][0]) < 1.5
        and abs(_ib.DOGRULAMA["TP yok  bt()"][1]
                - _ib.DOGRULAMA["TP yok  motor (madde 238 A)"][1]) < 0.05)
kontrol("madde 249: backtester TP AÇIK hâlde de motoru üretiyor (asıl doğrulama)",
        abs(_ib.DOGRULAMA["TP40/20 bt()"][0]
            - _ib.DOGRULAMA["TP40/20 motor (madde 249)"][0]) < 1.0
        and abs(_ib.DOGRULAMA["TP40/20 bt()"][1]
                - _ib.DOGRULAMA["TP40/20 motor (madde 249)"][1]) < 0.05)
kontrol("madde 249: TP hiç dolmayan seviyede TP-yok ile BİREBİR aynı (parite)",
        _ib.TP_MERDIVENI["TP 1000/1000"] == _ib.TP_MERDIVENI["TP yok"])
kontrol("madde 249: TP merdiveni doğru yönde - TP Sharpe'ı yükseltir, düşüşü azaltır",
        _ib.TP_MERDIVENI["TP 40/20"][1] > _ib.TP_MERDIVENI["TP yok"][1]
        and _ib.TP_MERDIVENI["TP 40/20"][2] > _ib.TP_MERDIVENI["TP yok"][2])
kontrol("madde 249: ters dolum fiyatı hatası KAYITLI ve felaket boyutunda",
        _ib.TP_HATALI[1] < -2.0 and "HATA 1" in _ib.__doc__
        and "LIMIT" in _ib.__doc__ and "STOP" in _ib.__doc__)
kontrol("madde 249: motorun ETKİLENMEDİĞİ yazılı ve g33.py gerçekten tam seviyeden dolar",
        "Motor etkilenmedi" in _ib.__doc__
        and "br[k]=sev/cv[i,k]-1" in open(os.path.join(R, "g33.py"),
                                          encoding="utf-8").read())
kontrol("madde 249: bt() artık STOP konvansiyonunu KULLANMIYOR",
        "min(sev, op)" not in open(os.path.join(R, "arastirma_ikinci_borsa.py"),
                                   encoding="utf-8").read().split("HATA 1")[-1])
kontrol("madde 249: OKX kitabı taşıyamıyor ($100M üstü < kitabın ihtiyacı)",
        _ib.OKX_EVREN["100M ustu"] < _ib.KITABIN_IHTIYACI)
kontrol("madde 249: darlık açıklama DEĞİL - Binance daraltılınca ~1 puan kaybediyor",
        abs(_ib.GENISLIK_TESTI["Binance kendi evreni"]
            - _ib.GENISLIK_TESTI["Binance OKX genisligine daraltilmis"]) < 2.0)
kontrol("madde 249: yayınlanan dağılım katı UZUN VADELİ olan (2,04), eşli pencere (4,05) değil",
        abs(_ib.DAGILIM["BINANCE (2022-07 -> 2026-08)"][1]
            / _ib.DAGILIM["OKX (2026-07/08)"][1] - 2.04) < 0.05
        and "2,04 KATI" in _ib.__doc__)
kontrol("madde 249: mekanizma OKX'te VAR - funding bacağı pozitif ve düzgün",
        _ib.OKX_FUNDING_BACAGI[0] > 0 and _ib.OKX_FUNDING_BACAGI[1] > 3.0)
kontrol("madde 249: sinyal TANIMI kıyası bozmuyor (iki formül 5 puan içinde)",
        abs(_ib.SINYAL_TANIMI_KIYASI["OKX formulu"][0]
            - _ib.SINYAL_TANIMI_KIYASI["sk_bar48"][0]) < 5.0)
kontrol("madde 249: 96 gün hüküm vermeye YETMEZ - kural kodda",
        _ib.hukum_verilebilir_mi() is False
        and _ib.hukum_verilebilir_mi(gun=800, sembol=40) is True)
kontrol("madde 249: ÇALIŞAN kitap 96 günde beşte bir negatif görünüyor",
        _ib.GUC_96GUN["negatif_olasilik"] > 20.0
        and _ib.GUC_96GUN["std"] > 2.0 and _ib.GUC_96GUN["ort"] > 1.0)
kontrol("madde 249: OKX'in negatif 96 günü BULGU OLARAK YAYINLANMIYOR",
        _ib.OKX_TAM_KITAP_96GUN[1] < 0 and "YAYINLANMAZ" in _ib.__doc__)
kontrol("madde 249: yeniden açma koşulu İKİ şartı birden istiyor",
        "2 YILI" in _ib.YENIDEN_ACMA_KOSULU and "30" in _ib.YENIDEN_ACMA_KOSULU
        and "ikisi birden" in _ib.YENIDEN_ACMA_KOSULU)
kontrol("madde 249: hacim birimi ve sahte sinyal hataları da kayıtlı",
        "HATA 2" in _ib.__doc__ and "HATA 3" in _ib.__doc__
        and "volCcyQuote" in _ib.__doc__)
kontrol("kâr haritası madde 249'u aynı duvarın üçüncü yüzü olarak yazdı",
        "MADDE 249" in _harita and "2,04 kat" in _harita
        and "Ölçülebilirlik (madde 249)" in _harita)

import arastirma_ortalama_dusurme as _od
kontrol("madde 250: ortalama düşürme adaylarının HİÇBİRİ şart 1'i geçmedi (7/7 RED)",
        _od.hicbiri_gecmedi() == [] and len(_od.MERDIVEN) == 7)
kontrol("madde 250: getiri artışı KALDIRAÇ - eşit riskte hepsi kontrolden kötü",
        _od.esit_riskte_hepsi_kotu()
        and all(v[6] < 1.0 for v in _od.MERDIVEN.values()))
kontrol("madde 250: merdiven monoton - agresifleşince düşüş artıyor",
        _od.MERDIVEN["esik %10 pay 0,5 ekleme 1"][4]
        < _od.MERDIVEN["esik %30 pay 0,5 ekleme 1"][4]
        and _od.MERDIVEN["esik %20 pay 1,0 ekleme 2"][4]
        < _od.MERDIVEN["esik %10 pay 0,5 ekleme 1"][4])
kontrol("madde 250: bootstrap bu adayı POZİTİF OLARAK kötü buldu (P(>0)<%10)",
        _od.BOOTSTRAP["p_pozitif"] < 10.0 and _od.BOOTSTRAP["ort"] < -10.0)
kontrol("madde 250: önceki redlerin hepsi AYIRT EDİLEMEZDİ (P>%40), bu değil",
        all(p > 40.0 for p in _od.ONCEKI_REDLER.values())
        and _od.BOOTSTRAP["p_pozitif"] < min(_od.ONCEKI_REDLER.values()))
kontrol("madde 250: ileri getiri aleyhlik derinliğiyle MONOTON kötüleşiyor",
        _od.monoton_kotulesme()
        and _od.ILERI_GETIRI["aleyhte >=%30"][0] < -5.0
        and _od.ILERI_GETIRI["kosulsuz"][2] > 50000)
kontrol("madde 250: yasa iki maddeyi birden anıyor (191 kes + 250 ekle)",
        "191" in _od.YASA and "250" in _od.YASA and "GIRIS" in _od.YASA)
kontrol("madde 250: girinti hatası KAYITLI ve dersi yazılı",
        "YANLIS GIRINTIYE" in _od.__doc__ and "PARITE TESTI DE YAKALAMAZDI" in _od.__doc__)
kontrol("madde 250: motor bayrağı var ve KAPALI varsayılan (parite korunur)",
        'EK_ESIK=float(os.environ.get("EK_ESIK","0"))'
        in open(os.path.join(R, "g33.py"), encoding="utf-8").read())
_g33 = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
kontrol("madde 250: DOLDUR bloğu EK_ESIK bloğunun İÇİNDE değil (girinti hatası geri gelmesin)",
        _g33.index("if DOLDUR and i+1<len") < _g33.index("if EK_ESIK>0:"))
kontrol("kâr haritası madde 250'nin yasasını iki yönlü yazdı",
        "MADDE 250" in _harita and "BOYUTUNA TUTMA SÜRESİNCE DOKUNULMAZ" in _harita
        and "monoton kötüleşir" in _harita)

import arastirma_risk_paritesi as _rp
import arastirma_yeniden_acma_defteri as _yd
kontrol("madde 251: risk paritesi cephesinin HEPSİ şart 1'i geçti (projede ilk)",
        _rp.hepsi_sart1_gecti() and len(_rp.CEPHE) == 7)
kontrol("madde 251: ama HİÇBİRİ eşit riskte kontrolü geçmedi (şart 3 vetosu)",
        _rp.esit_risk_kontrolu_gecen() == [])
kontrol("madde 251: cephe monoton ve limiti KONTROLÜN KENDİSİ",
        _rp.cephe_monoton()
        and _rp.CEPHE["1/(vol+0,50)"][5] < _rp.KONTROL["yillik"]
        and _rp.KONTROL["yillik"] - _rp.CEPHE["1/(vol+0,50)"][5] < 3.0)
kontrol("madde 251: Sharpe kazancı SAĞLAM ama eşit-risk farkı YAZI TURA",
        _rp.sharpe_saglam_para_degil())
kontrol("madde 251: şart 3 bu turda GERÇEK maliyet engelledi (madde 248'i düzeltir)",
        _rp.KONTROL["yillik"] - min(v[5] for v in _rp.CEPHE.values()) > 30.0)
kontrol("madde 251: motor bayrağı var ve varsayılan EŞİT (parite korunur)",
        'AGIRLIK=os.environ.get("AGIRLIK","esit")'
        in open(os.path.join(R, "g33.py"), encoding="utf-8").read())
kontrol("madde 251: risk paritesi taraf nötrlüğünü bozmuyor (taraf başına normalize)",
        "taban*_ag(lo); y[sh]=-taban*_ag(sh)"
        in open(os.path.join(R, "g33.py"), encoding="utf-8").read())
kontrol("madde 251: defterin YAPISAL SEÇİM kategorisi var ve ağırlığı kapsıyor",
        "bacak agirligi (esit para)" in _yd.YAPISAL_SECIM
        and len(_yd.YAPISAL_SECIM) >= 4)
kontrol("madde 251: her yapısal seçimin gerekçesi bir ÖLÇÜME işaret ediyor",
        _yd.yapisal_denetim() == [])
kontrol("madde 251: kavram kapsama haritası kalan boşlukları DÜRÜST işaretliyor "
        "(OI madde 252'de KAPANDI)",
        _rp.KAPSAM["acik pozisyon (OI)"][0].startswith("KAPALI")
        and _rp.KAPSAM["opsiyon turetilmisleri"][0].startswith("YAPISAL")
        and _rp.OI_KAPSAM["oran"] < 60)
kontrol("kâr haritası madde 251'in yasasını yazdı (Sharpe != para)",
        "MADDE 251" in _harita and "SHARPE İLE PARA AYNI ŞEY DEĞİL" in _harita)

import arastirma_acik_pozisyon as _oi
kontrol("madde 252: OI varyantlarının HİÇBİRİ şart 1'i geçmedi (3/3 RED)",
        _oi.ucu_de_red() == [] and len(_oi.VARYANT) == 3)
kontrol("madde 252: bootstrap en iyi varyantı POZİTİF OLARAK kötü buldu",
        _oi.BOOTSTRAP["p_pozitif"] < 15.0 and _oi.BOOTSTRAP["ort"] < -5.0)
kontrol("madde 252: ölçüm kitabın EN ZAYIF kısmı üzerinde - kapsam sınırı yazılı",
        _oi.evren_sinirli_mi() and _oi.KAPSAM["oran"] < 60
        and "GOSTERMEZ" in _oi.__doc__)
kontrol("madde 252: OI funding'in GÜRÜLTÜLÜ eşi - getiri aynı, Sharpe düşük",
        _oi.oi_fundingin_gurultulu_esi())
kontrol("madde 252: ders FİYAT/MİKTAR ayrımını kuruyor ve madde 220'ye bağlanıyor",
        "FIYATI" in _oi.DERS and "MIKTARI" in _oi.DERS and "220" in _oi.DERS)
kontrol("madde 252: motora bayrak EKLENMEDİ (SK_DOSYA ile beslendi)",
        "yeni bayrak EKLENMEDI" in _oi.__doc__ and "SK_DOSYA" in _oi.__doc__)
kontrol("madde 252: yeniden açma koşulu madde 253'te EMEKLİ edildi "
        "(kapsam zaten %97,7'ymiş)",
        "EMEKLI" in _oi.YENIDEN_ACMA_KOSULU and "253" in _oi.YENIDEN_ACMA_KOSULU)
kontrol("madde 251'in kapsama haritası OI'yi artık KAPALI gösteriyor",
        _rp.KAPSAM["acik pozisyon (OI)"][0].startswith("KAPALI")
        and "252" in _rp.KAPSAM["acik pozisyon (OI)"][1])
kontrol("kâr haritası madde 252'yi duvarın ÖLÇÜ eksenine ekledi",
        "MADDE 252" in _harita and "FİYAT mı MİKTAR mı" in _harita)

import arastirma_veri_kaynagi as _vk
kontrol("madde 253: fapi 451 ama Binance ARŞİVİ erişilebilir",
        _vk.arsiv_erisilebilir())
kontrol("madde 253: madde 252'nin kapsam gerekçesi YANLIŞTI ve kayıtlı",
        _vk.madde252_kapsam_iddiasi_yanlis()
        and _vk.GERCEK["kapsam"] > 95 and _vk.GERCEK["sembol"] > 600
        and "YANLISTI" in _vk.__doc__)
kontrol("madde 253: 252'nin yeniden açma koşulu EMEKLİ edildi",
        "EMEKLI" in _oi.YENIDEN_ACMA_KOSULU
        and "EMEKLI" in _vk.EMEKLI_KOSUL)
kontrol("madde 253: data_oi/ kullanılmaz olarak işaretli",
        "data_oi/" in _vk.KULLANILMAZ and "yaniltici" in _vk.KULLANILMAZ)
kontrol("madde 253: tam evrende de 3/3 RED - 252'nin SONUCU ayakta",
        _vk.ucu_de_red() == [] and len(_vk.VARYANT) == 3
        and _vk.BOOTSTRAP["p_pozitif"] < 25.0)
kontrol("madde 253: kalabalık ölçütü gerçek iş yapıyor (OI vekili kitabı yarıya indiriyor)",
        _vk.havuz_olcutu_is_yapiyor())
kontrol("madde 253: /tmp kırılganlığı için yeniden kurma reçetesi var",
        "metrik_panel" in _vk.YENIDEN_KURMA and "parite" in _vk.YENIDEN_KURMA
        and "metrics" in _vk.YOL and "fundingRate" in _vk.YOL)
kontrol("madde 253: ölçülen arşiv hızı kayıtlı (yeniden kurma planlanabilsin)",
        _vk.HIZ["dosya_saniye"] > 10 and _vk.HIZ["hata"] == 0)
kontrol("madde 251'in haritası OI'yi madde 253'e bağlıyor",
        "253" in _rp.KAPSAM["acik pozisyon (OI)"][1])
kontrol("kâr haritası madde 253'ün yöntem kuralını yazdı",
        "MADDE 253" in _harita and "ELDEKİNİ DENETLE" in _harita)

import arastirma_grafik_modeli as _gm
kontrol("madde 254: model gerçekten öğrendi (AUC plasebodan belirgin yüksek)",
        _gm.model_gercekten_ogrendi() and _gm.AUC["long"][0] > 0.75
        and _gm.ORNEK_DISI > 300000)
kontrol("madde 254: model GÜRÜLTÜYÜ yendi - grafik gerçek bilgi taşıyor",
        _gm.gurultuyu_yendi())
kontrol("madde 254: ama kontrole yenildi ve bootstrap kesin (P(>0)<%1)",
        _gm.kontrole_yenildi() and _gm.BOOTSTRAP["p_pozitif"] < 1.0
        and _gm.BOOTSTRAP["ort"] < -50.0)
kontrol("madde 254: LONG tarafta tahmin ile PARA ters yönlü",
        _gm.long_tahmin_parayla_ters()
        and _gm.UST_ALT["long"]["tp_kat"] > 25
        and _gm.UST_ALT["short"]["getiri_fark"] > 0)
kontrol("madde 254: hedef değişikliği kayıtlı (152 vs 254) ve 214'e bağlı",
        "214" in _gm.__doc__ and "62 tur" in _gm.__doc__
        and _gm.HEDEF_152 != _gm.HEDEF_254)
kontrol("madde 254: yasa İKİ soruyu birden soruyor (hedef + fiyatlanmışlık)",
        "(a)" in _gm.YASA and "(b)" in _gm.YASA and "FIYATLANMIS" in _gm.YASA)
kontrol("madde 254: motor modu var ve plasebo ikizi de var",
        "if ad in ('tpmdl','tpmdl_p'):"
        in open(os.path.join(R, "g33.py"), encoding="utf-8").read())
kontrol("madde 254: özellikler YALNIZCA grafik (funding/kalabalık kullanılmadı)",
        "KULLANILMAZ" in _gm.__doc__ or "KULLANILMADI" in _gm.__doc__)
kontrol("kâr haritası madde 254'ü tarama sırasına iki soru olarak ekledi",
        "MADDE 254" in _harita and "TERS olabilir" in _harita
        and "fiyatlanmış mı" in _harita)

import arastirma_grafik_kullanim as _gk
import karar_kurali as _kmod
kontrol("madde 255: taraf asimetrik seçim çöktü (iki uç da kaybediyor)",
        _gk.KULLANIM["taraf asimetrik secim"][0] < 40.0)
kontrol("madde 255: eleme MEKANİK - plasebo elemesi gerçeğinden kötü değil",
        _gk.eleme_mekanik_mi())
kontrol("madde 255: harman bilgisel - gerçek geçiyor, PLASEBO geçmiyor",
        _gk.harman_plasebodan_iyi_mi())
kontrol("madde 255: bilgi gerçek (plaseboya P>%80) ama para ayırt edilemez (kontrole P<%80)",
        _gk.para_ayirt_edilemez())
kontrol("madde 255: şart 3 veto etti ve w=0,25 BERABERE (fark <1 puan)",
        all(v == "esit riskte getiri" for v in _gk.KIRILAN_SART.values())
        and abs(_gk.KULLANIM["harman w=0,25"][5] - _gk.KONTROL["yillik"]) < 1.0)
kontrol("madde 255: 8 bakışta şart 1 geçişi DELİL taşımıyor",
        _gk.sart1_delil_tasimiyor() and _gk.BAKIS_SAYISI == 8)
kontrol("madde 255: motor/günlük Sharpe tuzağı yine kontrol edildi",
        _gk.MOTOR_VS_GUNLUK["harman w=0,50 motor"]
        > _gk.MOTOR_VS_GUNLUK["harman w=0,50 gunluk"])
kontrol("madde 255: çok bakış düzeltmesi KURALA girdi ve doğru hesaplıyor",
        abs(_kmod.cok_bakis_riski(8) - 86.6) < 0.5
        and _kmod.cok_bakis_riski(1) < _kmod.cok_bakis_riski(12)
        and _kmod.delil_mi(8, 68.0, 88.2)["sart1_delil_mi"] is False
        and _kmod.delil_mi(1, 85.0, 90.0)["sart1_delil_mi"] is True)
kontrol("madde 255: delil_mi iki soruyu AYRI cevaplıyor",
        _kmod.delil_mi(8, 68.0, 88.2)["kontrole_karsi_guclu"] is False
        and _kmod.delil_mi(8, 68.0, 88.2)["plaseboya_karsi_guclu"] is True)
kontrol("kâr haritası madde 255'i ön süzgeç/delil ayrımıyla yazdı",
        "MADDE 255" in _harita and "delil değil, ön süzgeçtir" in _harita)

import arastirma_kabul_denetimi as _kd
kontrol("madde 256: beş katmanın HEPSİ kuraldan (212) önce kabul edilmiş",
        len(_kd.kuraldan_once_kabul()) == 5 and _kd.KURAL_MADDESI == 212)
kontrol("madde 256: hiç yeniden açılmamış katman KALMADI (236 düzeltmesi)",
        _kd.hic_yeniden_acilmamis() == []
        and _kd.CIKARMA["uc hareket elemesi"][1] == 236)
kontrol("madde 256: havuz ve kâr al bootstrap'ta EZİCİ (P>%95)",
        _kd.KARAR["kalabalik havuzu"][2] > 95.0
        and _kd.KARAR["kar al (TP)"][2] > 95.0)
kontrol("madde 256: fırsat rezervi şart 4'ten düşüyor ama bootstrap destekliyor",
        _kd.KARAR["firsat rezervi"][0] is False
        and _kd.KARAR["firsat rezervi"][2] > _kd.BOOT_ESIK)
kontrol("madde 256: iki katman ölçülebilir NÖTR (iki yön de eşik altı)",
        sorted(_kd.gerekcesiz()) == ["emir akisi", "uc hareket elemesi"])
kontrol("madde 256: emir akışı BEDAVA - madde 228'in kopardığı bağ kayıtlı",
        "DONUK_ESIK" in _kd.AKIS_BEDAVA_SEBEBI
        and "228" in _kd.AKIS_BEDAVA_SEBEBI)
_cb256 = open(os.path.join(R, "carry_bot.py"), encoding="utf-8").read()
kontrol("madde 256: carry_bot gerçekten İKİ koşuldan biriyle veri topluyor",
        "if AKIS_AGIRLIK > 0 or DONUK_ESIK > 0:" in _cb256)
kontrol("madde 256: 236 hatası KAYITLI ve dersi defter/docstring ayrımı",
        "BENIM HATAM" in _kd.__doc__ and "MADDE 236" in _kd.__doc__
        and "DOCSTRING'IN KENDISI" in _kd.DERS)
kontrol("madde 256: görünür çelişkinin (sütun vs bootstrap) açıklaması yazılı",
        "normalize" in _kd.__doc__ and "bootstraptir" in _kd.__doc__)
kontrol("madde 256: her nötr katmanın yeniden açma koşulu var",
        set(_kd.YENIDEN_ACMA_KOSULU) >= set(_kd.gerekcesiz()))
kontrol("kâr haritası madde 256'yı çıkarma testi olarak yazdı",
        "MADDE 256" in _harita and "ÇIKARILIŞINDAN ölçülür" in _harita)

import arastirma_oynaklik_tilt as _ot
kontrol("madde 257: kitap ZATEN oynak coinleri seçiyor (1,40 kat tilt)",
        _ot.kitap_zaten_oynak_seciyor()
        and _ot.OYNAKLIK_OLCUMU["secilen 10 bacak"]
        > _ot.OYNAKLIK_OLCUMU["secilmeyen uygun"] * 1.25)
kontrol("madde 257: dört varyantın HİÇBİRİ şart 1'i geçmedi",
        _ot.dordu_de_red() == [] and len(_ot.VARYANT) == 4)
kontrol("madde 257: oynaklık YÖN olarak bilgi taşıyor (yüksek > sakin)",
        _ot.VARYANT["havuz olcutu = EN OYNAK"][0]
        > _ot.VARYANT["havuz olcutu = EN SAKIN"][0] + 25)
kontrol("madde 257: ASIL KIYAS - aynı riskte düz kaldıraç ÖNDE",
        _ot.kaldirac_onde_mi()
        and _ot.KALDIRAC_KIYASI["kontrol_getiri"]
        - _ot.KALDIRAC_KIYASI["aday_getiri"] > 15.0)
kontrol("madde 257: bootstrap iki ağırlık adayını da NEGATİF buldu",
        all(d < 0 and p < 40.0 for d, _, p in _ot.BOOTSTRAP.values()))
kontrol("madde 257: nokta tahmini yanıltıyor - madde 255'in kuralı uygulandı",
        _ot.nokta_tahmini_yaniltiyor() and _ot.BAKIS_SAYISI == 4)
kontrol("madde 257: yasa KALDIRAÇ kıyasını zorunlu kılıyor",
        "KALDIRACTIR" in _ot.YASA and "KENDI dususune" in _ot.YASA)
kontrol("madde 257: doğru adres madde 245'in doz cephesi ve 227'nin sırası",
        "245" in _ot.DOGRU_ADRES and "227" in _ot.DOGRU_ADRES)
kontrol("madde 257: motor modları eklendi ve parite korunuyor",
        'AGIRLIK=="volduz"' in open(os.path.join(R, "g33.py"),
                                    encoding="utf-8").read()
        and "elif ad in ('volsec','volsec_ters'):"
        in open(os.path.join(R, "g33.py"), encoding="utf-8").read())
kontrol("kâr haritası madde 257'yi kaldıraç kıyası yasası olarak yazdı",
        "MADDE 257" in _harita and "TİLT DEĞİL KALDIRAÇTIR" in _harita
        and "1,40 kat tilt" in _harita)

import arastirma_rejim_araci as _ra
kontrol("madde 258: kaldıraç yasası sicile uygulandı ve AYIRIYOR (250 hepsi altta)",
        len(_ra.YASA_SICILI) >= 18
        and all(v[4] < 0 for a, v in _ra.YASA_SICILI.items() if a.startswith("250")))
kontrol("madde 258: 239'un en güçlü adayı kaldıraçtan belirgin ÖNDE",
        _ra.YASA_SICILI["239 prim e1.0 ust2.0"][4] > 40.0)
kontrol("madde 258: yasa TEK BAŞINA yetmiyor - plasebo da geçiyor, marj eşiği var",
        _ra.PLASEBO_MARJI > 0
        and all(_ra.YASA_SICILI[a][4] > _ra.PLASEBO_MARJI
                for a in _ra.plaseboyu_asan()))
kontrol("madde 258: tam örnekte %80 eşiğini geçen aday YOK (en iyi %79,1)",
        _ra.tam_ornekte_gecen() == []
        and _ra.TAM_ORNEK["e0.5 ref180"][7] > 75.0)
kontrol("madde 258: boru hattı temiz - plasebonun bootstrap'ı yazı tura",
        abs(_ra.TAM_ORNEK["PLASEBO karis"][6]) < 3.0
        and 45.0 < _ra.TAM_ORNEK["PLASEBO karis"][7] < 60.0)
kontrol("madde 258: DÜŞÜK primde üç aday da eşiği geçiyor, plasebo geçmiyor",
        len(_ra.dusuk_primde_gecen()) == 3 and _ra.plasebo_ayrisiyor_mu())
kontrol("madde 258: en güçlü aday REJİM ARACI (bir rejimde güçlü, ötekinde negatif)",
        _ra.rejim_araci_mi("e1.0 ust2.0")
        and not _ra.rejim_araci_mi("PLASEBO karis"))
kontrol("madde 258: tetik ÖLÇÜM gerektiriyor, rejim tahminiyle açılmıyor",
        "YENIDEN OLCULUR" in _ra.TETIK and "TAHMINIYLE" in _ra.TETIK
        and "yeniden olc" in _ra.SINIR)
kontrol("madde 258: şart 1'in üçüncü yüzü KURALA girdi ve doğru sınıflıyor",
        _kmod.rejim_araci_mi(
            _kmod.Olcum("k", 112.3, 2.939, 2.789, 3.147, 14.5),
            _kmod.Olcum("a", 171.7, 3.033, 3.163, 3.006, 15.2),
            boot_p_dusuk=92.3)["sinif"] == "REJIM ARACI - KOSULLU"
        and _kmod.rejim_araci_mi(
            _kmod.Olcum("k", 112.3, 2.939, 2.789, 3.147, 14.5),
            _kmod.Olcum("b", 115.8, 2.705, 2.520, 2.956, 17.8),
            boot_p_dusuk=20.0)["sinif"] == "RED")
_rj = open(os.path.join(R, "arastirma_rejim.py"), encoding="utf-8").read()
kontrol("madde 258: rejim aracı artık SABİT kontrol dökümünü tercih ediyor",
        "/tmp/kontrol_E%d.pkl" in _rj and "UYARI" in _rj
        and "madde 258" in _rj)
kontrol("kâr haritası madde 258'i rejim sınıfı olarak yazdı",
        "MADDE 258" in _harita and "REJİME BAĞLI" in _harita
        and "REJİM ARACI — KOŞULLU" in _harita)

import arastirma_rejim_taramasi as _rt
kontrol("madde 259: tarama üç sınıfa ayırdı ve çoğunluk DÜZ RED",
        _rt.TARAMA["iki donemde kaybeden"] > _rt.TARAMA["tek donemde kaybeden"]
        and sum(_rt.TARAMA.values()) == 63)
kontrol("madde 259: tek dönemde kaybedenlerin dağılımı tarama ile tutarlı",
        sum(_rt.TEK_DONEM_DAGILIM.values()) == _rt.TARAMA["tek donemde kaybeden"])
kontrol("madde 259: kol rekonstrüksiyonu madde 244'ün kaydıyla BİREBİR",
        _rt.rekonstruksiyon_dogrulandi())
kontrol("madde 259: 244'ün kolu AYNI rejim imzasını taşıyor",
        _rt.ayni_imza_mi("kontrarian %20") and _rt.ayni_imza_mi("kontrarian %30"))
kontrol("madde 259: plasebo (işaret çevrilmiş) düşük primde eşiğin ALTINDA",
        _rt.plasebo_temiz_mi()
        and _rt.REJIM["PLASEBO izleyen %20"]["dusuk"][0] < 0)
kontrol("madde 259: AMA 244 eşiğe ulaşmıyor - sınıfa girmiyor",
        not _rt.esige_ulasiyor_mu()
        and _rt.REJIM["kontrarian %20"]["dusuk"][1] < _rt.BOOT_ESIK)
kontrol("madde 259: 239 aynı pencerede 244'ten belirgin güçlü",
        min(_rt.MADDE_239_DUSUK.values())
        > _rt.REJIM["kontrarian %20"]["dusuk"][1] + 10)
kontrol("madde 259: sınıfa giren YALNIZ madde 239'un varyantları (63'ten 3)",
        len(_rt.sinifa_giren()) == 3
        and all("244" not in a for a in _rt.sinifa_giren()))
kontrol("madde 259: üç kapı yazılı ve plasebo kapısını içeriyor",
        "ADAYLIK" in _rt.UC_KAPI and "%80" in _rt.UC_KAPI
        and "PLASEBO" in _rt.UC_KAPI)
kontrol("madde 259: kol eşitsizliği GEREKLİ ama YETERLİ DEĞİL olarak kayıtlı",
        "GEREKLI" in _rt.KOL_ESITSIZLIGI and "YETERLI DEGILDIR" in _rt.KOL_ESITSIZLIGI
        and "0,284" in _rt.KOL_ESITSIZLIGI)
kontrol("kâr haritası madde 259'u üç kapı olarak yazdı",
        "MADDE 259" in _harita and "ÜÇ KAPISI" in _harita
        and "Gerekli koşul, yeterli değil" in _harita)

import canli_karar as _ckr
kontrol("madde 260: bağlayıcı günler madde 216'nın güç tablosundan türüyor",
        _ckr.baglayici_gun("funding tahsilati") == 14
        and _ckr.baglayici_gun("TP orani LONG") == 30
        and _ckr.baglayici_gun("TP orani SHORT") == 60)
kontrol("madde 260: TOPLAM GETİRİ hiçbir zaman bağlayıcı değil (madde 151)",
        _ckr.baglayici_gun("toplam getiri") is None
        and _ckr.GUC["toplam getiri"][30] < 20.0)
kontrol("madde 260: getiri negatif ama funding tamsa karar DEVAM",
        _ckr.canli_gecer_mi(14, funding_gunluk=0.00071, dusus=6.2,
                            toplam_getiri=-40.0)["hukum"] == _ckr.DEVAM)
kontrol("madde 260: funding yarımsa 14. günde DURDUR",
        _ckr.canli_gecer_mi(14, funding_gunluk=0.00030)["hukum"] == _ckr.DURDUR)
kontrol("madde 260: funding TERS ise güç kapısı beklemez (1. günde DURDUR)",
        _ckr.canli_gecer_mi(1, funding_gunluk=-0.0001)["hukum"] == _ckr.DURDUR)
kontrol("madde 260: funding ölçütü 7. günde HENÜZ bağlayıcı değil",
        _ckr.canli_gecer_mi(7, funding_gunluk=0.00030)["sartlar"]
        ["L1 funding tahsilati"][0] == _ckr.DEVAM)
kontrol("madde 260: TP long 14'te bağlayıcı değil, 30'da İNCELE",
        _ckr.canli_gecer_mi(14, tp_long_oran=0.030)["hukum"] == _ckr.DEVAM
        and _ckr.canli_gecer_mi(30, tp_long_oran=0.030)["hukum"] == _ckr.INCELE)
kontrol("madde 260: düşüş koruması 1. GÜNDEN bağlayıcı (risk, performans değil)",
        _ckr.canli_gecer_mi(1, dusus=25.0)["hukum"] == _ckr.DURDUR)
kontrol("madde 260: p95 erken uyarı rayı çalışıyor",
        _ckr.canli_gecer_mi(14, dusus=9.1)["hukum"] == _ckr.INCELE
        and _ckr.canli_gecer_mi(14, dusus=5.0)["hukum"] == _ckr.DEVAM)
kontrol("madde 260: düşüş zarfı ufukla MONOTON artıyor",
        all(_ckr.DUSUS_ZARFI[a][3] < _ckr.DUSUS_ZARFI[b][3]
            for a, b in zip(sorted(_ckr.DUSUS_ZARFI), sorted(_ckr.DUSUS_ZARFI)[1:])))
kontrol("madde 260: 365 günlük zarf madde 243'ü teyit ediyor",
        abs(_ckr.DUSUS_ZARFI[365][0] - _ckr.MADDE_243_1YIL[0]) < 2.0
        and abs(_ckr.DUSUS_ZARFI[365][1] - _ckr.MADDE_243_1YIL[1]) < 1.5)
kontrol("madde 260: çıkış kodları hükümle eşleşiyor (gözetimsiz koşum)",
        _ckr.cikis_kodu({"hukum": _ckr.DEVAM}) == 0
        and _ckr.cikis_kodu({"hukum": _ckr.INCELE}) == 1
        and _ckr.cikis_kodu({"hukum": _ckr.DURDUR}) == 2)
_izl = open(os.path.join(R, "carry_izleme.py"), encoding="utf-8").read()
kontrol("madde 260: izleme aracı kararı çağırıp ÇIKIŞ KODU veriyor",
        "import canli_karar" in _izl and "sys.exit(main())" in _izl
        and "cikis_kodu" in _izl)
kontrol("madde 260: canlıya çıkış belgesi koşulabilir karara işaret ediyor",
        "MADDE 260" in _ham and "canli_karar.py" in _ham
        and "0 DEVAM" in _ham and "gözetimsiz" in _ham)

import arastirma_doz_tolerans as _dt
kontrol("madde 261: getiri sütunu madde 245'in cetvelini ORANSAL olarak üretiyor",
        _dt.dogrulama_245())
kontrol("madde 261: 1x'in bir yıllık p95'i madde 243'ün yayınladığıyla tutarlı",
        _dt.madde_243_tutarli())
kontrol("madde 261: düşüş ufukla MONOTON artıyor (her dozda)",
        all(all(_dt.p95(d, a) < _dt.p95(d, b)
                for a, b in zip(_dt.UFUKLAR, _dt.UFUKLAR[1:]))
            for d in _dt.DOZLAR))
kontrol("madde 261: düşüş dozla MONOTON artıyor (her ufukta)",
        all(all(_dt.p95(a, u) < _dt.p95(b, u)
                for a, b in zip(_dt.DOZLAR, _dt.DOZLAR[1:]))
            for u in _dt.UFUKLAR))
kontrol("madde 261: ufuk 3 KAT fark yaratıyor - 'ufuksuz soru anlamsız'",
        _dt.ufuk_ne_kadar_onemli() > 2.5)
kontrol("madde 261: bir yıllık -%20 tolerans 1x'in ALTINI gerektiriyor",
        _dt.en_yuksek_doz(365, 20) is None)
kontrol("madde 261: bir yıllık -%25 tolerans TAM 1,00x",
        _dt.en_yuksek_doz(365, 25) == 1.00)
kontrol("madde 261: kısa ufukta aynı tolerans ÇOK daha yüksek doz veriyor",
        _dt.en_yuksek_doz(14, 20) == 2.50)
kontrol("madde 261: doz önerisi madde 227'nin sırasını hatırlatıyor",
        "CANLI OLCUM ONCESINDE" in _dt.doz_onerisi(365, 25)["uyari"]
        and _dt.doz_onerisi(365, 25)["doz"] == 1.00)
kontrol("madde 261: 1x'in ALTI durumunda AGRESIF uyarısı veriliyor",
        "AGRESIF" in _dt.doz_onerisi(365, 20)["uyari"]
        and _dt.doz_onerisi(365, 20)["doz"] is None)
kontrol("madde 261: oransal doğrulama hatası KAYITLI",
        "ORANSAL test" in _dt.dogrulama_245.__doc__
        and "yanlis \"HAYIR\"" in _dt.dogrulama_245.__doc__)
kontrol("kâr haritası madde 261'i ufuk kuralı olarak yazdı",
        "MADDE 261" in _harita and "UFUKSUZ KURULAMAZ" in _harita
        and "üç girdi ister" in _harita)

kontrol("belge BAŞINDA neyin düzeltildiğini açıklıyor (bayatlığın kaydı)",
        "madde 217'de BAŞTAN YAZILDI" in _ham and "bakiye/75" in _ham
        and "madde 209" in _ham)

print("\n6g) MADDE 262 - YAYINLANAN SAYILARIN TEK KAYNAGI")
import arastirma_yayinlanan_sayilar as _ys

kontrol("madde 262: yayınlanan başlıklar depodaki seriden yeniden üretiliyor",
        _ys.dogrula() is True)
kontrol("madde 262: kaynak referans_getiri.csv, /tmp DEĞİL",
        _ys.SERI_DOSYA.endswith("referans_getiri.csv")
        and "/tmp" not in open(
            os.path.join(R, "arastirma_yayinlanan_sayilar.py"),
            encoding="utf-8").read().split('"""')[2])
kontrol("madde 262: serinin kendi ölçüleri yayınlananla birebir",
        abs(_ys.ozet()["yillik_getiri"] - 111.73) < 0.05
        and abs(_ys.ozet()["sharpe_gunluk"] - 2.892) < 0.005
        and abs(_ys.ozet()["maks_dusus"] + 14.27) < 0.05)
kontrol("madde 336: KAYIP ZEMİN kaydı silinmedi (112,46 ölçümü duruyor)",
        _ys.YAYINLANAN_KAYIP_ZEMIN["yillik_getiri"] == 112.5
        and _ys.YAYINLANAN_KAYIP_ZEMIN["sharpe_gunluk"] == 2.942
        and _ys.YAYINLANAN_KAYIP_ZEMIN["maks_dusus"] == -14.5
        and _ys.ZEMIN_YENIDEN_KURULDU is True)
kontrol("madde 336: ÖN KAYITLI geçit MOTOR ölçüsünde ve geçti",
        all(abs(v) < _ys.ZEMIN_PARITE_MOTOR_TOLERANS
            for v in _ys.ZEMIN_PARITE_MOTOR_FARK.values()))
kontrol("madde 336: SERİ ölçüsü geçidin KAPSAMINDA DEĞİL diye yazılı",
        _ys.ZEMIN_SERI_FARK_EN_BUYUK == 0.97
        and max(abs(v) for v in _ys.ZEMIN_FARK.values()) > _ys.ZEMIN_PARITE_MOTOR_TOLERANS
        and "KAPSAMINDA DEĞİL" in open(
            os.path.join(R, "arastirma_yayinlanan_sayilar.py"),
            encoding="utf-8").read())
kontrol("madde 336: iki ölçüyü karıştırma hatası KAYITLI",
        "önce ben" in open(
            os.path.join(R, "arastirma_yayinlanan_sayilar.py"),
            encoding="utf-8").read())
kontrol("madde 336: farkın sebebi İZOLE EDİLMEDİ diye kayıtlı",
        _ys.ZEMIN_FARK_SEBEBI_IZOLE is False
        and "İZOLE EDİLMEDİ" in open(
            os.path.join(R, "arastirma_yayinlanan_sayilar.py"),
            encoding="utf-8").read())
kontrol("madde 336: fark getiride KÖTÜ, düşüşte İYİ (zemin kitabı kayırmıyor)",
        _ys.ZEMIN_FARK["yillik_getiri"] < 0
        and _ys.ZEMIN_FARK["sharpe_gunluk"] < 0
        and _ys.ZEMIN_FARK["yil_getiri_p5"] < 0
        and _ys.ZEMIN_FARK["maks_dusus"] > 0)
kontrol("madde 262: kanonik yöntem ÖN KAYITLI (blok 21, B=20.000, tohum 11)",
        (_ys.KANONIK_BLOK, _ys.KANONIK_TEKRAR, _ys.KANONIK_TOHUM) == (21, 20000, 11))
kontrol("madde 262: getiri p5 tek değere bağlandı (madde 336: +%40,4)",
        _ys.YAYINLANAN["yil_getiri_p5"] == 40.4
        and _ys.YAYINLANAN_KAYIP_ZEMIN["yil_getiri_p5"] == 41.4)
kontrol("madde 262: iki kuyruk blok uzunluğuyla TERS yöne gidiyor",
        _ys.blok_ters_yonlu_mu() is True)
kontrol("madde 262: iki eksende birden ihtiyatlı TEK blok YOK",
        _ys.tek_blok_ihtiyatli_mi() is False)
kontrol("madde 262: belirsizliğin kaynağı BLOK (tohum değil)",
        _ys.gurultu_kaynagi() == "BLOK"
        and _ys.BLOK_GURULTUSU_PUAN > 5 * _ys.TOHUM_GURULTUSU_PUAN)
kontrol("madde 262: çapraz zarf her ekseni KENDİ en kötümserinden alıyor",
        _ys.CAPRAZ_ZARF["getiri_p5"][0]
        == min(_ys.BLOK_DUYARLILIK[b][0] for b in _ys.zarf_bloklari())
        and _ys.CAPRAZ_ZARF["dusus_p1"][0]
        == min(_ys.BLOK_DUYARLILIK[b][2] for b in _ys.zarf_bloklari())
        and _ys.ZARF_BLOK_UST == 90)
kontrol("madde 262: alarm eşikleri üç yöntemin p1'i arasında kalıyor",
        _ys.BLOK_DUYARLILIK[21][2] > -23.0 > _ys.MADDE_243["yil_dusus_p1"])
kontrol("madde 262: madde 243'ün iki ölçüsü AYRI ufuk olarak kayıtlı",
        "ufuk uzadıkça maksimum derinleşir" in _ys.__doc__
        and _ys.MADDE_243["gerceklesen_yuzdelik"] > 80)
kontrol("madde 262: /tmp'nin silindiği operasyonel bulgu kayıtlı",
        "kontrol_E" in _ys.__doc__ and "silinmiş" in _ys.__doc__)
kontrol("CANLIYA_CIKIS başlık tablosu madde 262'nin tek sayısını taşıyor",
        "+%41,4" in _ham and "MADDE 262" in _ham
        and "iki eksende birden ihtiyatlı tek bir blok" in _ham)
kontrol("kâr haritası madde 262'yi yöntem kuralı olarak yazdı",
        "MADDE 262" in _harita and "YÖNTEM SEÇİMİNİ DE YAYINLAMAKTIR" in _harita
        and "çapraz zarf" in _harita)

print("\n6h) MADDE 263 - MOMENTUM REDDI")
import arastirma_momentum as _mom

kontrol("madde 263: hüküm RED", _mom.hukum() == "RED")
kontrol("madde 263: 43 yapılandırmanın 43'ü long'da kaybetti",
        _mom.CEPHE_LONG_KAYBEDEN == _mom.CEPHE_TOPLAM == 43
        and _mom.EN_IYI_LONG_YILLIK < 0)
kontrol("madde 263: kullanıcının kurgusu ölçüldü ve kaybediyor",
        _mom.KULLANICI_KURGUSU["esik"] == 1.00
        and _mom.KULLANICI_KURGUSU["long_yillik"] < -50
        and _mom.KULLANICI_KURGUSU["short_yillik"] < 0)
kontrol("madde 263: aritmetik POZİTİF ama geometrik NEGATİF bir hücre var",
        _mom.aritmetik_pozitif_ama_geometrik_negatif() == [(5, 2.0)])
kontrol("madde 263: pompalanmış coin evrenden KÖTÜ (medyan ve kazanma oranı)",
        _mom.pompa_evrenden_kotu_mu() is True)
kontrol("madde 263: kullanıcının deneyimi ÇELİŞKİ DEĞİL diye kayıtlı",
        _mom.kullanicinin_deneyimi_aciklanabilir_mi() is True
        and _mom.HAM_ISARET[(5, 1.00)]["kazanma"] < _mom.EVREN[5]["kazanma"])
kontrol("madde 263: bulgunun kitapta TERS işaretle kullanıldığı kayıtlı",
        "UCELE" in _mom.kitap_bunu_zaten_kullaniyor_mu()
        and "ELEME" in _mom.kitap_bunu_zaten_kullaniyor_mu())
kontrol("madde 263: plasebo (long+short ayrı) ön kayıtta",
        "PLASEBO" in _mom.__doc__ and "stop" in _mom.__doc__.lower())
kontrol("kâr haritası madde 263'ü bileşiklenme yasası olarak yazdı",
        "MADDE 263" in _harita and "BİLEŞİKLENİR" in _harita
        and "MEDYANLA yaşar" in _harita)

print("\n6i) MADDE 264 - ZAMANLAMA")
import arastirma_zamanlama as _zm

kontrol("madde 264: haftalık tablo referans serisinden yeniden üretiliyor",
        _zm.dogrula() is True)
kontrol("madde 336: haftalık KAYIP ZEMİN kaydı silinmedi",
        _zm.HAFTALIK_KAYIP_ZEMIN["pozitif_ay_oran"] == 86.0
        and _zm.HAFTALIK_KAYIP_ZEMIN["pozitif_oran"] == 60.6)
kontrol("madde 336: haftalık YAPISAL değişmezler ayakta (6 hafta, 50 ay)",
        _zm.HAFTALIK["en_uzun_negatif_hafta"] == 6
        and _zm.HAFTALIK["ay"] == 50
        and _zm.ZEMIN_FARK_HAFTALIK["en_uzun_negatif_hafta"] == 0
        and _zm.ZEMIN_FARK_HAFTALIK["ay"] == 0)
kontrol("madde 336: pozitif AY oranı %86 -> %82 düştüğü ve SEBEBİ yazılı",
        _zm.HAFTALIK["pozitif_ay_oran"] == 82.0
        and _zm.ZEMIN_FARK_HAFTALIK["pozitif_ay_oran"] == -4.0
        and "bir ay = 2 puan" in open(
            os.path.join(R, "arastirma_zamanlama.py"),
            encoding="utf-8").read())
kontrol("madde 264: giriş saati ekseninde yalnız 2 hizalama var",
        _zm.HIZALAMA_SAYISI == 2 and _zm.DILIM_ARALIK_SAAT == 8
        and len(_zm.FAZ_OLCUM) == 2)
kontrol("madde 264: iki hizalama arasında anlamlı fark YOK",
        _zm.giris_saati_fark_eder_mi() is False
        and abs(_zm.FAZ_OLCUM[0]["getiri"] - _zm.FAZ_OLCUM[1]["getiri"]) < 0.5)
kontrol("madde 264: her iki hizalama İKİ dönemde de pozitif",
        all(_zm.FAZ_OLCUM[k]["e1"] > 0 and _zm.FAZ_OLCUM[k]["e2"] > 0
            for k in _zm.FAZ_OLCUM))
kontrol("madde 264: tutma süresi bir KALDIRAÇ KOLU (Sharpe sabit)",
        _zm.tutma_kaldirac_kolu_mu() is True)
kontrol("madde 264: haftalık kâr GARANTİ değil (haftanın ~%39'u eksi)",
        _zm.haftalik_kar_garanti_mi() is False
        and 55 < _zm.HAFTALIK["pozitif_oran"] < 65)
kontrol("madde 264: üst üste 6 negatif hafta kayda geçti",
        _zm.HAFTALIK["en_uzun_negatif_hafta"] == 6)
kontrol("madde 264: hüküm üç istek için ayrı ayrı yazılı",
        _zm.hukum() == {"giris_saati": "RED", "kisa_dongu": "RED",
                        "haftalik_nakit": "ZATEN VAR"})
kontrol("kâr haritası madde 264'ü eksen-genişliği yasası olarak yazdı",
        "MADDE 264" in _harita and "sadece İKİ nokta" in _harita
        and "kenar değil DOZ" in _harita)

print("\n6j) MADDE 265 - DAKIKA COZUNURLUKLU DOLUM")
import arastirma_dolum as _dl

kontrol("madde 265: üretimin merdiveni botun GERÇEK sabitleriyle aynı",
        _dl.LIMIT_OFSET == cb.LIMIT_OFSET
        and _dl.MERDIVEN == cb.GTX_DENEME_CARPANLARI
        and _dl.BEKLEME_DK * 60 == cb.DOLUM_BEKLEME_SN
        and len(_dl.MERDIVEN) == cb.DOLUM_DENEME + 1)
kontrol("madde 265: maker dolum %82,6 ve piyasaya düşme %17,4 kayıtlı",
        abs(_dl.OLCUM["maker_oran"] - 82.6) < 0.05
        and abs(_dl.OLCUM["piyasa_oran"] - 17.4) < 0.05
        and _dl.OLCUM["n"] > 5000)
kontrol("madde 265: varsayım İYİMSER çıktı (+0,498bp ~ 0,79 puan/yıl)",
        _dl.SAPMA_BP > 0 and abs(_dl.SAPMA_BP - 0.498) < 0.002
        and 0.7 < _dl.SAPMA_PUAN_YIL < 0.9)
kontrol("madde 265: sapma madde 213'ün 3,3 puanlık eksen bütçesinin İÇİNDE",
        _dl.SAPMA_PUAN_YIL < 3.3)
kontrol("madde 265: maliyetin tamamı piyasaya düşenlerden",
        _dl.maliyetin_kaynagi()["piyasa_katkisi_bp"] > 2.5
        and _dl.maliyetin_kaynagi()["maker_katkisi_bp"] < 0)
kontrol("madde 265: ölçülen dolum oranı ÜST SINIR (kuyruk yok sayıldı)",
        _dl.dolum_orani_ust_sinir_mi() is True
        and "kuyru" in _dl.__doc__.lower()
        and "TABAN" in _dl.hukum().upper() + _dl.__doc__.upper())
kontrol("madde 265: dolum oranını maksimize etmek maliyeti minimize ETMİYOR",
        _dl.MERDIVEN_CEPHESI["yalniz_5bp_9dk"][0]
        > _dl.MERDIVEN_CEPHESI["uretim_5_10_20_9dk"][0]
        and _dl.MERDIVEN_CEPHESI["yalniz_5bp_9dk"][1]
        > _dl.MERDIVEN_CEPHESI["uretim_5_10_20_9dk"][1])
kontrol("madde 265: bekleme bir ADAY, öneri DEĞİL ve canlı testi yazılı",
        "ADAY" in _dl.aday_canli_testi()
        and "CARRY_DOLUM_BEKLEME" in _dl.aday_canli_testi()
        and "canli olcumden once VERILMEZ" in
        _dl.aday_canli_testi().replace("ı", "i").replace("İ", "I")
        .replace("ö", "o").replace("ü", "u").replace("ç", "c"))
kontrol("madde 265: hüküm ayarın DEĞİŞMEDİĞİNİ söylüyor",
        "DEĞİŞMEDİ" in _dl.hukum())
kontrol("kâr haritası madde 265'i icra yasası olarak yazdı",
        "MADDE 265" in _harita
        and "MALİYETİ MİNİMİZE ETMEK DEĞİLDİR" in _harita
        and "TABAN" in _harita)

print("\n6k) MADDE 266 - GUN ICI DUSUS ve LIKIDASYON")
import arastirma_icgun as _ig

kontrol("madde 266: gün içi düşüş günlük kapanıştan KÖTÜ (büyütme > 1)",
        _ig.OLCUM["buyutme_medyan"] > 1.0
        and _ig.OLCUM["dk1_medyan"] < _ig.OLCUM["g1_medyan"]
        and _ig.OLCUM["dk1_en_kotu"] < _ig.OLCUM["g1_en_kotu"])
kontrol("madde 266: büyütme sabit çarpan DEĞİL (p90 ve maks çok daha yüksek)",
        _ig.OLCUM["buyutme_p90"] > 2.0 and _ig.OLCUM["buyutme_max"] > 5.0)
kontrol("madde 266: KASKAD hipotezi ÇÜRÜDÜ ve bu kayda geçti",
        _ig.kaskad_hipotezi_tuttu_mu() is False
        and abs(_ig.KASKAD["sepet_kaybi_medyan"]) < 1.0
        and _ig.KASKAD["sembol_sayisi"] >= 7)
kontrol("madde 266: dibi TEK SEMBOL yapıyor (40 tohumun yarısından çoğu aynı gün)",
        _ig.KASKAD["dibi_yapan_tohum"] > _ig.OLCUM["tohum"] // 2)
kontrol("madde 266: likidasyon eşiği formülü doğru (1+g*r <= mmr*g)",
        abs(_ig.likidasyon_esigi(2.0, 0.010) + 49.0) < 0.1
        and abs(_ig.likidasyon_esigi(1.0, 0.010) + 99.0) < 0.1)
kontrol("madde 266: likidasyon p95 yolunda 3x'e kadar BAĞLAYICI DEĞİL",
        all(not _ig.likidasyon_baglayici_mi(g) for g in _ig.P95_GUNLUK))
kontrol("madde 266: ölçülen KUYRUK 2,5x ve 3x'te likide ederdi, 2x'te etmez",
        _ig.kuyruk_likide_eder_mi(2.50) is True
        and _ig.kuyruk_likide_eder_mi(3.00) is True
        and _ig.kuyruk_likide_eder_mi(2.00) is False)
kontrol("madde 266: p95 gün içi tahmini doz tablosunu büyütüyor",
        _ig.p95_icgun(1.00) > _ig.P95_GUNLUK[1.00]
        and abs(_ig.p95_icgun(1.00) - 31.2) < 0.3)
kontrol("madde 266: ZIT YÖNLÜ iki sapma yazılı, net düzeltme iddia EDİLMİYOR",
        set(_ig.sapma_yonu()) == {"yukari", "asagi"}
        and "TAVAN" in _ig.sapma_yonu()["yukari"]
        and "IDDIA EDILMIYOR" in _ig.__doc__.replace("İ", "I").replace("Ç", "C")
        .replace("ı", "i").replace("Ğ", "G"))
kontrol("kâr haritası madde 266'yı gün içi yasası olarak yazdı",
        "MADDE 266" in _harita and "GÜN İÇİ YOLU GÖSTERMEZ" in _harita
        and "TEK İSİM" in _harita)

kontrol("madde 266: doz aracı gün içi kısıtını SÖYLÜYOR",
        "1,49" in _dt.icgun_uyarisi(1.00)
        and "LİKİDASYON" in _dt.icgun_uyarisi(2.50)
        and "LİKİDASYON" not in _dt.icgun_uyarisi(2.00))

print("\n6l) MADDE 267 - KAR-AL DOLUMU")
import arastirma_tp_dolum as _tpd

kontrol("madde 267: TP eşikleri motorun GERÇEK ayarlarıyla aynı",
        abs(_tpd.TP_LONG["esik"] - cb.KAR_AL_ORAN) < 1e-9
        and abs(_tpd.TP_SHORT["esik"] - cb.KAR_AL_SHORT) < 1e-9)
kontrol("madde 267: kullanılacak bakiyelerde TP dolumu GÜVENLİ",
        _tpd.tp_guvenli_mi(10000) is True
        and _tpd.tp_guvenli_mi(100000) is True)
kontrol("madde 267: 1M$ ve 5M$'da GÜVENLİ DEĞİL (kapasite kısıtı)",
        _tpd.tp_guvenli_mi(1000000) is False
        and _tpd.tp_guvenli_mi(5000000) is False)
kontrol("madde 267: gerçek TP hacmi marjinalin en az 10 KATI",
        _tpd.marjinal_mi_gercek_mi() > 10.0)
kontrol("madde 267: marjinal dokunuşların ~%40'ı TEK DAKİKA (kırılgan altküme)",
        35 < _tpd.MARJINAL["tek_dakika_oran"] < 45)
kontrol("madde 267: 5 günlük tutma TP ulaşma p95'ini KAPSIYOR",
        _tpd.tutma_suresi_yetiyor_mu() is True
        and _tpd.TP_LONG["ulasma_saat_p95"] > 100
        and _tpd.TUTMA_GUN * 24 == 120)
kontrol("madde 267: kapasite kısıtı TP dolumunda diye kayıtlı",
        "madde 204" in _tpd.kapasite_sinirini_ne_belirliyor()
        and "DAHA" in _tpd.kapasite_sinirini_ne_belirliyor())
kontrol("madde 267: kuyruk derinliğinin ÖLÇÜLEMEDİĞİ ve duyarlılık verildiği yazılı",
        "kuyruk" in _tpd.__doc__.lower() and "duyarl" in _tpd.__doc__.lower()
        and set(_tpd.TP_DOLMAMA_LONG[10000]) == {1, 10, 50, 100})
kontrol("madde 267: örneklem sınırı (olay sayısı ve 2 ay) kayıtlı",
        _tpd.TP_LONG["olay"] < 500 and "2 ay" in _tpd.__doc__
        and "SINIRLAR" in _tpd.__doc__)
kontrol("madde 267: hüküm ayarın DEĞİŞMEDİĞİNİ söylüyor",
        "DEĞİŞMEDİ" in _tpd.hukum())
kontrol("kâr haritası madde 267'yi en-pahalı-satır yasası olarak yazdı",
        "MADDE 267" in _harita and "EN PAHALI SATIRI" in _harita
        and "19 kat" in " ".join(_harita.split()))

print("\n6m) MADDE 268 - FUNDING MUHASEBESI")
import arastirma_funding_muhasebe as _fm

kontrol("madde 268: muhasebe kimliği tutuyor (ham == panel)",
        _fm.kimlik_tutuyor_mu() is True
        and abs(_fm.TUM_PANEL["fark_pct"]) < 1.0
        and abs(_fm.UYGUN_EVREN["fark_pct"]) < 1.0)
kontrol("madde 268: ÖRNEKLEM ŞARTI var (n=0 ile 'geçti' engellenmiş)",
        _fm.ornek_yeterli_mi() is True
        and _fm.dogrula() is True)
kontrol("madde 268: ızgara hatası YOK",
        _fm.izgara_hatasi_var_mi() is False)
kontrol("madde 268: hata olsaydı bedeli ~7 puan diye kayıtlı",
        6.0 < _fm.IZGARA_HATASI_OLSAYDI_PUAN < 8.0
        and _fm.BRUT_FUNDING_PUAN == 109.8)
kontrol("madde 268: ölçülen sapma 1 puanın ÇOK altında",
        _fm.kacirilan_puan() < 0.5)
kontrol("madde 268: panelin GERÇEK kaynağı kayıtlı ve eskisinden ayrı",
        _fm.KAYNAK_DIZIN == "data_funding_genis"
        and _fm.KAYNAK_SUTUN == "funding"
        and _fm.ESKI_DIZIN == "data_funding")
kontrol("madde 268: iki sütun-adı hatası kayda geçti",
        len(_fm.HATALAR) == 2
        and "date" in _fm.HATALAR[0]
        and "data_funding_genis" in _fm.HATALAR[1])
kontrol("madde 268: hüküm ayarın DEĞİŞMEDİĞİNİ söylüyor",
        "DEĞİŞMEDİ" in _fm.hukum() and "TEMİZ" in _fm.hukum())
kontrol("kâr haritası madde 268'i sıfır-örneklem yasası olarak yazdı",
        "MADDE 268" in _harita
        and "SIFIR ÖRNEKLEMLE GELEN" in _harita
        and "VERİ KAYNAĞI da denetlenmeli" in _harita)

print("\n6n) MADDE 269 - EVREN TAMLIGI")
import arastirma_evren_tamlik as _et

kontrol("madde 269: aritmetik kapanıyor (847 + 54 = 901)",
        _et.aritmetik_kapaniyor_mu() is True
        and _et.PANEL_SEMBOL == 847 and _et.ARSIV["usdt"] == 901)
kontrol("madde 269: eksiğin TAMAMI sınıflandırıldı",
        _et.siniflandirma_tam_mi() is True
        and _et.EKSIK_SINIF["gercek_bosluk"] == 1)
kontrol("madde 269: arşiv BUDANMAMIŞ ve kanıtı yazılı",
        _et.arsiv_budanmis_mi() is False
        and "BZRX" in _et.BUDANMAMIS_KANIT and "2020" in _et.BUDANMAMIS_KANIT)
kontrol("madde 269: bar boyutu da denetlendi ve temiz",
        _et.bar_boyutu_temiz_mi() is True
        and len(_et.BAR_DENETIMI["delist_ornekleri"]) >= 5)
kontrol("madde 269: bulunan boşluk funding ucunda DEĞİL, marjinal",
        _et.bosluk_funding_ucunda_mi() is False
        and _et.bosluk_marjinal_mi() is True)
kontrol("madde 269: boşluğun büyüklüğü ÖLÇÜLDÜ (funding çekildi)",
        _et.BOSLUK["odeme_sayisi"] > 1000
        and _et.BOSLUK["ciro_medyan_musd"] > 100
        and _et.BOSLUK["ornek_ici_ay"] == 11)
kontrol("madde 269: madde 146'nın ZATEN düzelttiği kayda geçti",
        _et.MADDE_146["gercek_delist"] == 156
        and _et.MADDE_146["guven_yeni"] == "MEDIUM-HIGH"
        and _et.MADDE_146["arsiv_dondurur_silmez"] is True)
kontrol("madde 269: açılış hatam açıkça yazıldı",
        "28" in _et.ACILIS_HATASI and "madde 146" in _et.ACILIS_HATASI
        and "last_valid_index" in _et.ACILIS_HATASI)
kontrol("madde 269: yöntem farkı (örnekleme vs tüketme) kayıtlı",
        "ÖRNEKLEME" in _et.MADDE_146["yontem"]
        and "TÜKETME" in _et.BU_TURUN_YONTEMI)
kontrol("madde 269: yeniden açma şartı somut",
        "yeniden indiril" in _et.yeniden_acma_sarti()
        and "kontrol koşusu" in _et.yeniden_acma_sarti())
kontrol("madde 269: doğrulama geçiyor ve ayar değişmedi",
        _et.dogrula() is True and "DEĞİŞMEDİ" in _et.hukum())
kontrol("kâr haritası madde 269'u kaynağa-bak yasası olarak yazdı",
        "MADDE 269" in _harita
        and "EN SON MADDESİ OKUNUR" in _harita
        and "847+54=901" in " ".join(_harita.split()))

print("\n6o) MADDE 270 - KULLANICININ IKINCI BOTU")
import arastirma_kullanici_botu as _kb

kontrol("madde 270: sinyal POZİTİF ama hesap NEGATİF (boyut sorunu)",
        _kb.sinyal_pozitif_mi() is True
        and _kb.HESAP["boyut25_yillik_pct"] < 0
        and _kb.sorun_sinyal_mi_boyut_mu() == "BOYUT")
kontrol("madde 270: kullanıcının boyutu optimumun ~5 katı",
        4.0 < _kb.boyut_kac_kat_buyuk(0.30) < 6.0
        and _kb.en_iyi_boyut(_kb.BOYUT_CEPHESI_30)[0] == 0.05)
kontrol("madde 270: ±%40'ta optimum %10 ve pozitif",
        _kb.en_iyi_boyut(_kb.BOYUT_CEPHESI_40)[0] == 0.10
        and _kb.BOYUT_CEPHESI_40[0.10][0] > 5.0)
kontrol("madde 270: boyut cephesi MONOTON değil (Kelly tepesi var)",
        _kb.BOYUT_CEPHESI_30[0.05][0] > _kb.BOYUT_CEPHESI_30[0.025][0]
        and _kb.BOYUT_CEPHESI_30[0.05][0] > _kb.BOYUT_CEPHESI_30[0.25][0])
kontrol("madde 270: STOP faydalı çıktı ve kayıtlı",
        _kb.stop_faydali_mi() is True
        and _kb.HESAP["stop_yok_iflas"] is True)
kontrol("madde 270: 1 gün tutma 3 günden iyi",
        _kb.HESAP["boyut25_yillik_pct"] > _kb.HESAP["tutma3g_yillik_pct"])
kontrol("madde 270: boşluk ölçüldü ve kriptoda yok diye kayıtlı",
        _kb.BOSLUK_OLCUMU["mutlak_25_ustu_bar_pct"] < 0.01
        and "IYIMSER" in _kb.BOSLUK_OLCUMU["yorum"])
kontrol("madde 270: BENİM ÜÇ HATAM kayda geçti",
        len(_kb.BENIM_UC_HATAM) == 3
        and "GUNDE BIR" in _kb.BENIM_UC_HATAM[2])
kontrol("madde 270: kaldıraç iması aritmetikle yazılı",
        _kb.KALDIRAC_IMA["coin_10_hareket_icin_kaldirac"] == 10.0
        and "−%50" in _kb.KALDIRAC_IMA["ters_ucta"])
kontrol("madde 270: madde 241'in −%743'ü referans olarak kayıtlı",
        _kb.MADDE_241["en_kotu_tek_islem"] == -743.0
        and _kb.MADDE_241["pump_short_ortalama"] < 5.0)
kontrol("kâr haritası madde 270'i boyut yasası olarak yazdı",
        "MADDE 270" in _harita
        and "BÜYÜK BOYUT BİRLEŞİNCE" in _harita
        and "HATA SİNYALİDİR" in _harita)

print("\n6p) MADDE 271 - KOLUN SHARPE ESIGI")
import arastirma_kol_esigi as _ke

kontrol("madde 271: korelasyon madde 200'ün kapısını GEÇİYOR",
        _ke.korelasyon_kapisi_geciyor_mu() is True and _ke.KORELASYON < 0.10)
kontrol("madde 271: hiçbir pay şart 1'i geçmiyor",
        _ke.hicbir_pay_gecmiyor_mu() is True)
kontrol("madde 271: %5'te Sharpe İYİLEŞİYOR ama bootstrap GÜRÜLTÜ diyor",
        _ke.HARMAN[0.05][1] > _ke.HARMAN[0.00][1]
        and _ke.bes_pay_iyilesmesi_gurultu_mu() is True
        and _ke.BOOTSTRAP[0.05][3] < 50.0)
kontrol("madde 271: üç eşik var ve en yükseği BAĞLAYICI",
        _ke.baglayici_esik() == _ke.ESIK_ESITRISK_SAGLAM
        and _ke.ESIK_ESITRISK_SAGLAM > _ke.ESIK_SHARPE_SAGLAM > _ke.ESIK_NOKTA)
kontrol("madde 271: eşik taraması MONOTON (P yükseliyor)",
        all(_ke.ESIK_TARAMA[a][1] < _ke.ESIK_TARAMA[b][1]
            for a, b in zip(sorted(_ke.ESIK_TARAMA), sorted(_ke.ESIK_TARAMA)[1:])))
kontrol("madde 271: kol eşiğin ALTINDA ve kaç kat uzak olduğu hesaplanıyor",
        _ke.kol_gecer_mi(_ke.KOL["sharpe"], _ke.KORELASYON)["gecer"] is False
        and _ke.kol_gecer_mi(_ke.KOL["sharpe"], _ke.KORELASYON)["kat"] > 4.0)
kontrol("madde 271: eşiği GEÇEN bir kol kabul edilir (fonksiyon çalışıyor)",
        _ke.kol_gecer_mi(2.5, 0.07)["gecer"] is True
        and _ke.kol_gecer_mi(2.5, 0.15)["gecer"] is False)
kontrol("madde 271: kalibrasyon dışı girdide UYARI veriyor",
        len(_ke.kol_gecer_mi(2.5, 0.07, pay=0.20)["uyari"]) > 0
        and len(_ke.kol_gecer_mi(2.5, 0.07)["uyari"]) == 0)
kontrol("madde 271: madde 200'ün EKSİK olduğu ve red serisinin aritmetik olduğu kayıtlı",
        "EKSİK" in _ke.madde_200_eksik_mi()
        and "ARİTMETİK" in _ke.madde_200_eksik_mi()
        and 241 in _ke.REDDEDILEN_KOLLAR and 270 in _ke.REDDEDILEN_KOLLAR)
kontrol("madde 271: yöntem hatam (çarpmak Sharpe'ı değiştirmez) kayıtlı",
        "ÇARPTIM" in _ke.YONTEM_HATAM and "DEĞİŞMEZ" in _ke.YONTEM_HATAM)
kontrol("madde 271: hüküm RED ve ayar değişmedi",
        "RED" in _ke.hukum() and "DEĞİŞMEDİ" in _ke.hukum())
kontrol("kâr haritası madde 271'i Sharpe tabanı yasası olarak yazdı",
        "MADDE 271" in _harita and "SHARPE TABANI" in _harita
        and "ARİTMETİK" in _harita)

print("\n6r) MADDE 272 - 4. SARTIN ARKASINDAKI ODA")
import arastirma_dorduncu_sart as _ds

kontrol("madde 272: merdiven AÇILMADI (iki şart daha var)",
        _ds.merdiven_acildi_mi() is False
        and _ds.DORDUNCU_SARTA_CARPANLAR["merdiven %20 x1/2"]["diger_engel"])
kontrol("madde 272: rezervin TEK engeli kaldıraçtı",
        _ds.rezerv_tek_engeli_kaldirac_miydi() is True)
kontrol("madde 272: MOTOR Sharpe ile GÜNLÜK Sharpe çelişiyor (4. kez)",
        _ds.motor_gunluk_celiskisi()["celiski"] is True
        and _ds.motor_gunluk_celiskisi()["motor_fark"] > 0
        and _ds.motor_gunluk_celiskisi()["gunluk_fark"] < 0)
kontrol("madde 272: eşit-risk kazancı bootstrap ÇITASINI geçiyor",
        _ds.esit_risk_saglam_mi() is True
        and _ds.BOOTSTRAP["d_esitrisk_P"] >= _ds.GUC_CITASI)
kontrol("madde 272: ΔSharpe sıfırdan ayırt EDİLEMİYOR",
        _ds.sharpe_farki_gurultu_mu() is True)
kontrol("madde 272: likidasyon 1,298x'te BAĞLAYICI DEĞİL",
        _ds.likidasyon_baglayici_mi() is False
        and _ds.LIKIDASYON["esik_mmr1_pct"] < -70
        and _ds.LIKIDASYON["madde266_en_kotu_kuyruk_pct"]
        > _ds.LIKIDASYON["esik_mmr1_pct"])
kontrol("madde 272: kaldıracın İCRA bedeli brütle ölçeklenip düşülmüş",
        abs(_ds.ICRA["sapma_130x_puan"]
            - _ds.ICRA["sapma_1x_puan"] * _ds.ESIT_RISK["kaldirac"]) < 0.02
        and _ds.net_kazanc() < _ds.BOOTSTRAP["d_esitrisk_ort"])
kontrol("madde 272: net kazanç ~+2 puan ve madde 230 PLATOSUNUN İÇİNDE",
        1.5 < _ds.net_kazanc() < 2.5 and _ds.plato_icinde_mi() is True)
kontrol("madde 272: dürüst okuma madde 265'in düzeltmesini taşıyor",
        abs(_ds.DURUST_OKUMA["kontrol"] - 111.7) < 0.2
        and _ds.DURUST_OKUMA["aday"] > _ds.DURUST_OKUMA["kontrol"])
kontrol("madde 272: hüküm KALDIRAÇ kararı diyor ve ayar DEĞİŞTİRİLMEDİ",
        "KALDIRAC karari" in _ds.hukum()
        and "DEGISTIRILMEDI" in _ds.hukum())
kontrol("madde 272: motorun ayarı gerçekten değişmemiş (rezerv 0,20)",
        abs(cb.REZERV - 0.20) < 1e-9 if hasattr(cb, "REZERV") else True)
kontrol("kâr haritası madde 272'yi vekil-şart yasası olarak yazdı",
        "MADDE 272" in _harita
        and "YENİDEN AÇILIR" in _harita
        and "vekil" in _harita.lower())

print("\n6s) MADDE 273 - NAKIT KADRANI + KALDIRAC")
import arastirma_nakit_kadrani as _nk

kontrol("madde 273: motor Sharpe cephenin SONUNA kadar yükseliyor",
        all(_nk.MOTOR[a][1] < _nk.MOTOR[b][1]
            for a, b in zip(sorted(_nk.MOTOR), sorted(_nk.MOTOR)[1:])))
kontrol("madde 273: eşit-risk getirisi monoton yükseliyor",
        all(_nk.CEPHE[a][1] < _nk.CEPHE[b][1]
            for a, b in zip(sorted(_nk.CEPHE), sorted(_nk.CEPHE)[1:])))
kontrol("madde 273: likidasyon duvarı madde 266'nın kuyruğundan türetiliyor",
        abs(_nk.duvar(0.010) - 2.358) < 0.01
        and _nk.MADDE_266_KUYRUK < -40)
kontrol("madde 273: rezerv 0,70 duvarı AŞIYOR, 0,60 aşmıyor",
        _nk.duvari_asiyor_mu(0.70) is True
        and _nk.duvari_asiyor_mu(0.60) is False)
kontrol("madde 273: en iyi GÜVENLİ nokta rezerv 0,60",
        abs(_nk.en_iyi_guvenli() - 0.60) < 1e-9
        and 5.0 < _nk.CEPHE[0.60][3] < 6.5)
kontrol("madde 273: Δeşit-risk çıtayı geçiyor ama NET geçmiyor",
        _nk.esitrisk_citayi_geciyor_mu(0.60) is True
        and _nk.net_citayi_geciyor_mu(0.60) is False)
kontrol("madde 273: kaldıraç KANITI da zayıflatıyor (kayıtlı)",
        _nk.kaldirac_kaniti_zayiflatiyor_mu(0.60) is True)
kontrol("madde 273: şart 1 rezervle KÖTÜLEŞİYOR",
        _nk.sart1_kotulesyor_mu() is True)
kontrol("madde 273: eşit risk düşüşü eşitliyor (gün içi her satırda AYNI)",
        abs(_nk.GUN_ICI - _nk.HEDEF_DUSUS * 1.488) < 0.05
        and "kaldiracla carptim" in _nk.BENIM_HATAM)
kontrol("madde 273: icra bedeli kaldıraçla ölçeklenmiş",
        all(abs(_nk.CEPHE[r][2] - 0.79 * _nk.CEPHE[r][0]) < 0.03
            for r in _nk.CEPHE))
kontrol("madde 273: hüküm KALDIRAÇ kararı ve ayar DEĞİŞTİRİLMEDİ",
        "KALDIRAC karari" in _nk.hukum()
        and "DEGISTIRILMEDI" in _nk.hukum())
kontrol("kâr haritası madde 273'ü kuyruk-duvarı yasası olarak yazdı",
        "MADDE 273" in _harita
        and "KUYRUK DUVARI BELİRLER" in _harita
        and "KANITI da zayıflatır" in _harita)

print("\n6t) MADDE 274 - OLCUT BAGIMLILIGI")
import arastirma_olcut_bagimliligi as _ob

kontrol("madde 274: aynı aday ölçütler arasında İŞARET değiştiriyor",
        _ob.isaret_degistiriyor_mu() is True
        and _ob.oynaklikta_negatif_mi() is True)
kontrol("madde 274: maks düşüş EN İYİMSER ölçüt",
        max(_ob.OLCUT_CEPHESI, key=lambda o: _ob.OLCUT_CEPHESI[o][0.60])
        == "maks dusus")
kontrol("madde 274: doz ölçütünde kazanç madde 273'ün yarısından AZ",
        _ob.doz_olcutunde_kuculuyor_mu() is True
        and _ob.DOZ_OLCUTUNDE_KAZANC < 2.0)
kontrol("madde 274: rezerv0,60 duvarı −%30'da aşıyor",
        _ob.duvari_hangi_toleransta_asiyor("rezerv60") == 30)
kontrol("madde 274: kontrol bu aralıkta duvarı HİÇ aşmıyor",
        _ob.duvari_hangi_toleransta_asiyor("kontrol") is None
        and _ob.kontrol_daha_genis_mi() is True)
kontrol("madde 274: doz çetvelinde rezerv AYNI toleransta DAHA FAZLA brüt istiyor",
        all(_ob.DOZ[t][2] > _ob.DOZ[t][0] for t in _ob.DOZ))
kontrol("madde 274: sakin sürüş TAKASI kayıtlı (p95 düşer, getiri de düşer)",
        _ob.sakin_surus_takasi()["p95_dusus"][1]
        < _ob.sakin_surus_takasi()["p95_dusus"][0]
        and _ob.sakin_surus_takasi()["getiri"][1]
        < _ob.sakin_surus_takasi()["getiri"][0])
kontrol("madde 274: hüküm rezerv 0,20'nin KALDIĞINI ve 273'ün düzeltildiğini söylüyor",
        "0,20 KALIYOR" in _ob.hukum() and "DUZELTILDI" in _ob.hukum())
kontrol("madde 274: motorun rezervi gerçekten 0,20",
        abs(cb.REZERV - 0.20) < 1e-9 if hasattr(cb, "REZERV") else True)
kontrol("kâr haritası madde 274'ü ölçüt yasası olarak yazdı",
        "MADDE 274" in _harita
        and "RİSK ÖLÇÜTÜNÜ DEĞİŞTİR" in _harita
        and "KARARIN ölçütü" in _harita)

print("\n6u) MADDE 275 - FUNDING KESKIN NISANCILIGI")
import arastirma_funding_snipe as _fs

kontrol("madde 275: gelir asgari gidiş-dönüş maliyetinin ONDA BİRİ mertebesinde",
        _fs.OLCUM["gelir_bp"] * 5 < _fs.ASGARI_MALIYET_BP)
kontrol("madde 275: işi bitiren MALİYET, ters seçilim DEĞİL (fiyat lehte)",
        _fs.maliyet_mi_olduruyor() is True
        and _fs.kalabalik_etkisi_var_mi() is False
        and _fs.OLCUM["fiyat_bp"] > 0)
kontrol("madde 275: sıfır kaymayla ve imkânsız maker ile BİLE net negatif",
        _fs.sifir_kaymayla_bile_olu_mu() is True
        and _fs.imkansiz_maker_ile_bile_olu_mu() is True
        and _fs.DUYARLILIK["kayma_yok_5bp_taker"][1] < 0
        and _fs.DUYARLILIK["kayma_yok_2bp_maker"][1] < 0)
kontrol("madde 275: arz yok - ödemelerin %97'den fazlası 10bp eşiğini geçemiyor",
        _fs.arz_var_mi() is False and _fs.ARZ[10] < 3.0)
kontrol("madde 275: arz taraması TÜM evrende yapıldı (yüzlerce sembol, milyonlarca ödeme)",
        _fs.ARZ_SEMBOL > 800 and _fs.ARZ_ODEME > 2_000_000)
kontrol("madde 275: arz oranları eşikle birlikte MONOTON azalıyor",
        all(_fs.ARZ[a] >= _fs.ARZ[b]
            for a, b in zip(sorted(_fs.ARZ), sorted(_fs.ARZ)[1:])))
kontrol("madde 275: uç kuyruk hakkında hüküm VERİLEMEZ (n cok kucuk)",
        _fs.uc_kuyruk_hukum_verilebilir_mi() is False)
kontrol("madde 275: tutma tabanı ~1,8 gün ve kitabın 5 günü tabanın ÜSTÜNDE",
        1.0 < _fs.tutma_tabani_gun() < 3.0
        and _fs.tutma_taban_ustunde_mi() is True
        and _fs.KITAP_TUTMA_GUN == 5)
kontrol("madde 275: hüküm RED ve YAPISAL, ayar değişmedi",
        "RED" in _fs.hukum() and "yapisal" in _fs.hukum()
        and "DEGISMEDI" in _fs.hukum())
kontrol("kâr haritası madde 275'i asgari maliyet yasası olarak yazdı",
        "MADDE 275" in _harita
        and "ASGARİ MALİYET" in _harita
        and "asgari gidiş-dönüş maliyeti" in _harita)

print("\n6v) MADDE 276 - DOZ KARARI")
import arastirma_doz_karari as _dk

kontrol("madde 276: doz girdisinin VERİ KAYNAĞI denetlendi (madde 268)",
        _dk.kaynak_denetlendi_mi() is True)
kontrol("madde 276: madde 274'ün nokta çözümü bağımsız tohumlarla yeniden üretildi",
        _dk.madde_274_dogrulandi_mi() is True
        and _dk.monte_carlo_yayilimi() < 0.05)
kontrol("madde 276: ÖRNEKLEME belirsizliği Monte Carlo gürültüsünden 10 kat BÜYÜK",
        _dk.belirsizlik_gurultuden_buyuk_mu() is True
        and _dk.ornekleme_yayilimi() > 0.5)
kontrol("madde 276: karar brütü örneklemenin İHTİYATLI ucundan (p5) alındı",
        _dk.ihtiyatli_doz_secildi_mi() is True
        and _dk.KARAR_BRUT < _dk.BRUT_ARALIK["medyan"])
kontrol("madde 276: karar brütü likidasyon duvarının İÇİNDE, pay >40 puan",
        _dk.duvarin_icinde_mi() is True
        and _dk.PAY[1.254][0.010] > 40.0
        and _dk.duvarin_yuzde_kaci() < 60.0)
kontrol("madde 276: duvar formülü madde 266'nın kuyruğuyla tutarlı",
        abs(_dk.duvar_hesapla(0.010) - _dk.DUVAR[0.010]) < 0.01)
kontrol("madde 276: gün içi karşılığı GÜNLÜK toleranstan derin (madde 266 büyütmesi)",
        _dk.gun_ici_karsiligi()[1] > _dk.TOLERANS
        and abs(_dk.GUN_ICI_MEDYAN - _dk.TOLERANS * _dk.BUYUTME_MEDYAN) < 1e-6)
kontrol("madde 276: iki kuyruk ölçütü ÜST ÜSTE BİNDİRİLMEDİ (p90 çarpımı yok)",
        _dk.GUN_ICI_MEDYAN < _dk.TOLERANS * _dk.BUYUTME_P90
        and "CARPMADIM" in _dk.BENIM_YAPMADIGIM_HATA)
kontrol("madde 276: gerçekleşen yol p95'ten SIĞ (madde 243'ün şanslı yolu)",
        abs(_dk.GERCEKLESEN[1.254][1]) < _dk.TOLERANS)
kontrol("madde 276: VARSAYILAN brüt 1,0'da kaldı ve motor da öyle",
        _dk.varsayilan_degismedi_mi() is True
        and abs(cb.GROSS_EXPOSURE - 1.0) < 1e-9)
kontrol("madde 276: borsa kaldıracı karar brütünde yeterli pay bırakıyor",
        cb.gerekli_kaldirac() >= 1)
kontrol("madde 276: hüküm dozu VE varsayılanın kaldığını söylüyor",
        "1.25x" in _dk.hukum() and "1,0'da KALDI" in _dk.hukum())
_cbkaynak = open(os.path.join(R, "carry_bot.py"), encoding="utf-8").read()
_gpos = _cbkaynak.index('GROSS_EXPOSURE = float(')
_gbelge = _cbkaynak[_gpos:_gpos + 4000]
kontrol("madde 276: GROSS_EXPOSURE belgesindeki bayat madde 149 tablosu DÜZELTİLDİ",
        "MADDE 276" in _gbelge
        and "TABLOSU BAYAT" in _gbelge
        and "+%111,7" in _gbelge
        and "CARRY_GROSS=1.25" in _gbelge)
kontrol("canlıya çıkış belgesi doz kararını ve kapısını yazdı",
        "CARRY_GROSS=1.25" in _ham
        and "MADDE 276" in _ham
        and "1,254x" in _ham)
kontrol("kâr haritası madde 276'yı örnekleme-aralığı yasası olarak yazdı",
        "MADDE 276" in _harita
        and "ÖRNEKLEME ARALIĞINI" in _harita
        and "TEKRARLANABİLİRLİK DOĞRULUK DEĞİLDİR" in _harita)

print("\n6w) MADDE 277 - OLAY KOLU GERCEK ICRA")
import arastirma_olay_icra as _oi
import carry_olay as _co

kontrol("madde 277 KUSUR: CARRY_OLAY_PAY varsayılanı artık 0 (eskiden 0,20)",
        abs(_co.PAY) < 1e-12
        and _oi.kusur_duzeltildi_mi() is True
        and _oi.KUSUR["eski_varsayilan"] == 0.20)
kontrol("madde 277: kol kapalıyken bacak büyüklüğü SIFIR",
        abs(_co.bacak_usd(10000.0)) < 1e-12)
_cokaynak = open(os.path.join(R, "carry_olay.py"), encoding="utf-8").read()
kontrol("madde 277: belge ile kod artık AYNI şeyi söylüyor",
        'os.getenv("CARRY_OLAY_PAY", "0.0")' in _cokaynak
        and "VARSAYILAN 0 = KAPALI" in _cokaynak
        and "MADDE 277" in _cokaynak
        and '"0.20"' not in _cokaynak.split("ESIK =")[0])
kontrol("madde 277: funding geliri ile fiyat hareketi birbirini GÖTÜRÜYOR",
        _oi.funding_fiyati_goturuyor_mu() is True
        and abs(_oi.GOTURME) < 2.0)
kontrol("madde 277: götürme ÖLÇEKTEN BAĞIMSIZ (madde 214 ile aynı yapı)",
        _oi.goturme_olcekten_bagimsiz_mi() is True)
kontrol("madde 277: uç funding dilimde fiyat hareketi geliri AŞIYOR",
        _oi.uc_funding_pahali_mi() is True
        and _oi.doz_tepki_monoton_mu() is True)
kontrol("madde 277: maker dolumu TERS SEÇİLİMİN kendisi",
        _oi.maker_dolumu_ters_secilim_mi() is True
        and _oi.OLCUM["maker_dolum_pct"] > 95.0)
kontrol("madde 277: üç ön kayıtlı eşiğin ÜÇÜ DE RED",
        _oi.esik_1_net() is False and _oi.esik_2_sharpe() is False
        and _oi.esik_3_iki_donem() is False
        and _oi.kol_acilir_mi() is False)
kontrol("madde 277: her yıl negatif (şart 1 tartışmasız)",
        _oi.her_yil_negatif_mi() is True and len(_oi.YILLAR) == 5)
kontrol("madde 277: madde 166'nın KENDİ Sharpe'i de kol tabanının ALTINDA",
        _oi.madde_166_kendi_rakamiyla_gecer_miydi() is False
        and _oi.MADDE_166["sharpe"] < _oi.KOL_TABANI)
kontrol("madde 277: kendi hatam İYİMSER yöndeydi ve kayıtlı",
        _oi.hatam_iyimser_miydi() is True
        and "ileriye bakis" in _oi.HATAM["ne"])
kontrol("madde 277: örneklem madde 275'in boşluğundan 100 kat büyük",
        _oi.ornek_madde_275ten_buyuk_mu() is True
        and _oi.OLCULEN_OLAY > 20000)
kontrol("madde 277: hüküm kolun ÖLÜ olduğunu ve ayarın değişmediğini söylüyor",
        "OLU" in _oi.hukum() and "DEGISMEDI" in _oi.hukum())
kontrol("kâr haritası madde 277'yi ölçek-bağımsız götürme yasası olarak yazdı",
        "MADDE 277" in _harita
        and "ÖLÇEKTEN BAĞIMSIZDIR" in _harita
        and "HASATTAN" in _harita)

print("\n6x) MADDE 278 - UYARLANABILIR OGRENME KAHINI")
import arastirma_uyarlanabilir as _uy

kontrol("madde 278: kontrol paritesi motorun bugünkü ayarıyla aynı",
        abs(_uy.KONTROL_PARITE["yillik"] - 112.3) < 0.5
        and abs(cb.REBALANCE_HOURS / 24.0 - 5.0) < 1e-9)
kontrol("madde 278: kâhin tavanı BÜYÜK (en az bir ailede >10 puan)",
        _uy.kahin_tavani_buyuk_mu() is True
        and _uy.en_yuksek_tavan()[0] == "reb")
kontrol("madde 278: tutma ekseninde kazanç DOZ DEĞİL (düşüş de iyileşiyor)",
        _uy.tavan_doz_mu("reb") is False
        and abs(_uy.KAHIN["reb"][1]) < abs(_uy.KAHIN["reb"][0]))
kontrol("madde 278: çoklu kâhin ÜST SINIR olarak etiketli ve tek aileden büyük",
        _uy.COKLU_UST_SINIR_PUAN > _uy.KAHIN["reb"][4]
        and "OLCUM DEGIL" in open("arastirma_uyarlanabilir.py",
                                  encoding="utf-8").read())
kontrol("madde 278: dönem optimumu geçmişten TAHMİN EDİLEMİYOR (üç test)",
        _uy.tahmin_edilebilir_mi() is False
        and _uy.RHO_P > 0.05 and _uy.ISABET_P > 0.05
        and abs(_uy.RHO_TOPLAM) < 0.15)
kontrol("madde 278: argmax isabeti ŞANS seviyesinde",
        abs(_uy.ISABET[0] / _uy.ISABET[1] * 100 - _uy.ISABET_SANS_PCT) < 5.0)
kontrol("madde 278: GÜÇ sınırı kayıtlı - güçlü elendi, ılımlı ELENEMEDİ",
        _uy.guclu_tahmin_elendi_mi() is True
        and _uy.ilimli_tahmin_elendi_mi() is False)
kontrol("madde 278: gerçekçi öğrenici kontrolden GERİDE, çoğu ailede kaybediyor",
        _uy.ogrenici_kaybediyor_mu() is True
        and _uy.kac_ailede_kaybediyor() >= 3)
kontrol("madde 278: madde 231'in modeli SEVİYE atlaması seçiyor -> öğrenici geride",
        _uy.rejim_mi_trend_mi() == "seviye"
        and _uy.ogrenici_yapisal_olarak_geride_mi() is True)
kontrol("madde 278: tasarım sınırı (amaç/ölçüt uyuşmazlığı) KAYITLI",
        "SHARPE" in _uy.TASARIM_SINIRI
        and "bulgu DEGIL" in _uy.TASARIM_SINIRI
        and _uy.KAHIN["rezerv"][4] < 0)
kontrol("madde 278: madde 152'nin ML kaydı elle kuralın ALTINDA",
        max(_uy.MADDE_152["ridge"], _uy.MADDE_152["gbm"])
        < _uy.MADDE_152["elle_kural"])
kontrol("madde 278: hüküm RED ve ayarın değişmediğini söylüyor",
        "RED" in _uy.hukum() and "DEGISMEDI" in _uy.hukum()
        and "ULASILAMIYOR" in _uy.hukum())
kontrol("kâr haritası madde 278'i tahmin-edilebilirlik yasası olarak yazdı",
        "MADDE 278" in _harita
        and "TAHMİN EDİLEBİLİRLİĞİNİ DE ÖLÇ" in _harita
        and "İKİNCİ ADIM" in _harita)

print("\n6y) MADDE 279 - EMIR DEFTERI DERINLIGI")
import arastirma_defter_derinligi as _dd
import karar_kurali as _kk279

kontrol("madde 279: veri kapsaması yeterli (%90 üstü) ve sızıntı önlemi kayıtlı",
        _dd.kapsama_yeterli_mi() is True
        and "BIR GUN kaydirildi" in _dd.VERI["sizinti_onlemi"]
        and _dd.VERI["alinan_cift"] / _dd.VERI["istenen_cift"] > 0.95)
kontrol("madde 279: defter TEK BAŞINA kontrolden yüksek Sharpe veriyor",
        _dd.defter_tek_basina_calisiyor_mu() is True
        and "dd5" in _dd.tek_basina_calisanlar())
kontrol("madde 279: işaret ölçümle çözüldü (biri çalışıp tersi çöküyor)",
        _dd.isaret_belirsiz_miydi() is True
        and _dd.ADAY["dd5"][1] > 3 * _dd.ADAY["dd5_ters"][1])
kontrol("madde 279: AMA aynı prim - korelasyon madde 200'ün kapısını GEÇMİYOR",
        _dd.ayni_prim_mi() is True
        and _dd.korelasyon_kapisini_geciyor_mu("dd5") is False
        and _dd.korelasyon_kapisini_geciyor_mu("dd1") is False)
kontrol("madde 279: harmanda Sharpe yükselirken PARA sabit kalıyor",
        _dd.sharpe_yukselirken_para_sabit_mi() is True
        and _dd.harman_gurultunun_icinde_mi() is True
        and _dd.EN_IYI_HARMAN_KAZANC < _dd.GURULTU_BANDI)
kontrol("madde 279: şart 1'i geçen TEK aday var ve o da şart 2+3'ten düşüyor",
        _dd.sart1_gecen() == ["dd1"]
        and _dd.sart2_gecer_mi("dd1") is False
        and _dd.sart3_gecer_mi("dd1") is False)
kontrol("madde 279: DÖRT ŞARTI geçen aday YOK",
        _dd.dort_sart_gecen() == [])
kontrol("madde 279: çokluk ÖN KAYITTA beyan edildi ve tek geçiş DELİL DEĞİL",
        _dd.BAKIS == 10
        and _dd.tek_gecis_delil_mi() is False
        and abs(_kk279.cok_bakis_riski(_dd.BAKIS) - _dd.COK_BAKIS_RISKI) < 1.0)
kontrol("madde 279: madde 220'nin BEŞİNCİ yüzü olarak kaydedildi",
        _dd.kacinci_yuz() == 5 and len(_dd.MADDE_220_YUZLER) == 4)
kontrol("madde 279: aggTrades'in ölçeklenemediği kayıtlı",
        _dd.aggtrades_olceklenir_mi() is False and _dd.AGGTRADES_MB > 10)
kontrol("madde 279: madde 253'ün kalabalık ölçümü gerekçe olarak kayıtlı",
        _dd.MADDE_253_OI[0] > 100 and _dd.MADDE_253_OI[1] < 50)
kontrol("madde 279: hüküm RED ve ayarın değişmediğini söylüyor",
        "RED" in _dd.hukum() and "DEGISMEDI" in _dd.hukum()
        and "AYNI PRIM" in _dd.hukum())
kontrol("kâr haritası madde 279'u korelasyon yasası olarak yazdı",
        "MADDE 279" in _harita
        and "EKLEMEK DEMEK DEĞİLDİR" in _harita
        and "KORELASYONU" in _harita)

print("\n6z) MADDE 280 - DEVRE KESICI")
import arastirma_devre_kesici as _dk280

kontrol("madde 280: kendi hatam (D=15/20 hiç tetiklemedi) KAYITLI",
        _dk280.hatam_kayitli_mi() is True
        and len(_dk280.TETIKLEMEYENLER) == 4)
kontrol("madde 280: gerçekleşen yolda düşüş İYİLEŞMEDİ",
        _dk280.gerceklesen_dusus_iyilesti_mi() is False
        and _dk280.GERCEKLESEN["D10_f0.25"][3] > _dk280.GERCEKLESEN["kontrol"][3])
kontrol("madde 280: SEKİZ varyantın SEKİZİ de doz ölçütünde kaybediyor",
        _dk280.hepsi_kaybediyor_mu() is True and _dk280.BAKIS == 8)
kontrol("madde 280: en iyi varyant bile NEGATİF",
        _dk280.en_iyi_varyant()[1] < 0)
kontrol("madde 280: kayıp TETİKLEME sıklığıyla artıyor (doz-tepki tek yönlü)",
        _dk280.kayip_tetiklemeyle_artiyor_mu() is True)
kontrol("madde 280: AYNI brütte hepsi p95 düşüşü ARTIRIYOR",
        _dk280.ayni_brutte_dususu_artiriyor_mu() is True)
kontrol("madde 280: medyan düşüşe faydası YOK",
        _dk280.medyan_dususe_faydasi_var_mi() is False)
kontrol("madde 280: MEKANİZMA zirve - düşüşü artıranlar az zirve + çok sualtı",
        _dk280.mekanizma_zirve_mi() is True
        and _dk280.MEKANIZMA["D10_f0.25"][3] < _dk280.MEKANIZMA["kontrol"][3]
        and _dk280.MEKANIZMA["D10_f0.25"][4] > _dk280.MEKANIZMA["kontrol"][4])
kontrol("madde 280: ÇİFTE KAYIP (hem getiri hem kuyruk)",
        _dk280.cifte_kayip_mi() is True)
kontrol("madde 280: bedava kuyruk azaltma YOK, iki yol kayıtlı",
        _dk280.bedava_kuyruk_azaltma_var_mi() is False
        and len(_dk280.KUYRUK_AZALTMANIN_IKI_YOLU) == 2)
kontrol("madde 280: KİRLENME uyarısı - blok brütü doz tavsiyesi DEĞİL",
        "doz tavsiyesi DEGIL" in _dk280.KIRLENME_UYARISI
        and _dk280.BLOK_KONTROL_BRUT > _dk280.MADDE_276_KARISTIRMA_BRUT
        > _dk280.MADDE_276_DOZ_BRUT)
kontrol("madde 280: doz kararı madde 276 ile tutarlı (1,25x)",
        abs(_dk280.MADDE_276_DOZ_BRUT - 1.254) < 1e-9)
kontrol("madde 280: madde 191/215 genelleştirildi ve hüküm RED",
        _dk280.GENELLESTIRILEN == (191, 215)
        and "RED" in _dk280.hukum() and "DEGISMEDI" in _dk280.hukum())
kontrol("kâr haritası madde 280'i zirve yasası olarak yazdı",
        "MADDE 280" in _harita
        and "DÜŞÜŞÜ ARTIRIR" in _harita
        and "YENİ ZİRVE YAPAMAZ" in _harita)

_cbg33 = open(os.path.join(R, "g33.py"), encoding="utf-8").read()
print("\n6aa) MADDE 281 - BACAK ASIMETRISI")
import arastirma_bacak_asimetrisi as _ba

kontrol("madde 281: iki bacak AYNI işlem değil (short net > long net)",
        _ba.iki_bacak_ayni_mi() is False
        and _ba.short_bacak_daha_karli_mi() is True)
kontrol("madde 281: dolar nötrlüğü motorun kodunda korunuyor",
        "taban/len(lo)" in _ba.DOLAR_NOTR_SATIR
        and "y[lo]=taban/len(lo)" in _cbg33)
kontrol("madde 281: asimetri etkisi İŞARET DEĞİŞTİRİYOR, tanımlanamıyor",
        _ba.asimetri_isaret_degistiriyor_mu() is True
        and _ba.asimetri_tanimlanabilir_mi() is False)
kontrol("madde 281: eşleştirilmiş kontrast kullanıldı (3 çift, aynı toplam bacak)",
        len(_ba.KONTRAST) == 3
        and all(int(a[1]) + int(a[4]) == int(b[1]) + int(b[4])
                for a, b in _ba.KONTRAST))
kontrol("madde 281: Sharpe farkları sıfıra yakın (doz değil kenar YOK)",
        _ba.sharpe_farklari_sifira_yakin_mi() is True)
kontrol("madde 281: eşit riskte üstün GÖRÜNEN var ama doz ölçütünde YOK",
        len(_ba.esit_riskte_ustun_gorunen()) > 0
        and _ba.doz_olcutunde_ustun_var_mi() is False)
kontrol("madde 281: kontrol 5+5 doz ölçütünde OPTİMUM",
        _ba.kontrol_doz_optimumu_mu() is True
        and _ba.DOZ["L5_S5"][2] == 0.0)
kontrol("madde 281: L3_S3'ün üstünlüğü doz ölçütünde İŞARET ÇEVİRDİ",
        _ba.olcut_tuzagi_isaret_cevirdi_mi() is True
        and _ba.OLCUT_TUZAGI["madde_281_L3_S3"][1] < 0)
kontrol("madde 281: madde 274'ün yasası İKİNCİ KEZ doğrulandı",
        _ba.ikinci_dogrulanma_mi() is True
        and len(_ba.OLCUT_TUZAGI) == 2)
kontrol("madde 281: L3_S3 tek coin yoğunlaşmasıyla da BLOKE (madde 192)",
        _ba.yogunlasma_bloke_mi("L3_S3") is True
        and _ba.DOZ["L3_S3"][3] >= _ba.MADDE_192_RED_ESIGI)
kontrol("madde 281: çok bakış beyan edildi (6 asimetrik aday)",
        _ba.ASIMETRIK_BAKIS == 6 and _ba.COK_BAKIS_RISKI > 70.0)
kontrol("madde 281: motorun bacak sayısı gerçekten 5+5",
        cb.N_LEGS == 5)
kontrol("madde 281: hüküm RED ve ayarın değişmediğini söylüyor",
        "RED" in _ba.hukum() and "DEGISMEDI" in _ba.hukum()
        and "TANIMLANAMIYOR" in _ba.hukum())
kontrol("kâr haritası madde 281'i ölçüt-yanlılığı yasası olarak yazdı",
        "MADDE 281" in _harita
        and "OYNAKLIĞI ARTIRAN ADAYLARI KAYIRIR" in _harita
        and "SON KAPI DOZ" in _harita.upper())

print("\n6ab) MADDE 282 - BUYUKLUK AGIRLIGI")
import arastirma_buyukluk_agirligi as _bg

kontrol("madde 282: YENİ motor kolu varsayılanı ETKİSİZ (SK_GAMMA=0)",
        _bg.ayar_degismedi_mi() is True
        and 'SK_GAMMA=float(os.environ.get("SK_GAMMA","0"))' in _cbg33
        and 'AGIRLIK=="buyukluk"' in _cbg33)
kontrol("madde 282: yeni kol taraf başına NORMALİZE (dolar nötrlüğü korunur)",
        "y[lo]=taban*_agb(lo); y[sh]=-taban*_agb(sh)" in _cbg33
        and "normalize" in _bg.YENI_KOL["notrluk"])
kontrol("madde 282: İKİ parite de BİREBİR geçti",
        _bg.parite_gecti_mi() is True and len(_bg.PARITE) == 2)
kontrol("madde 282: KRİTİK parite - YENİ kod yolu gamma=0'da kontrolü veriyor",
        _bg.yeni_kod_yolu_dogrulandi_mi() is True)
kontrol("madde 282: getiri fırlıyor AMA şart 1'i HİÇBİRİ geçmiyor",
        _bg.getiri_firliyor_mu() is True and _bg.sart1_gecen() == [])
kontrol("madde 282: erken dönem (22-24) Sharpe'ı gamma ile MONOTON yıkılıyor",
        _bg.erken_donem_monoton_yikiliyor_mu() is True
        and _bg.IZGARA["g2.0_k0"][2] < 2.0)
kontrol("madde 282: eşit riskte üstün GÖRÜNEN var ama doz ölçütünde YOK",
        len(_bg.esit_riskte_ustun_gorunen()) > 0
        and _bg.doz_olcutunde_pozitif_var_mi() is False)
kontrol("madde 282: doz ölçütündeki kayıp gamma ile MONOTON büyüyor",
        _bg.doz_monoton_mu() is True)
kontrol("madde 282: MEKANİZMA - gizlenmiş bacak azaltma ve DEĞİŞKEN",
        _bg.gizlenmis_bacak_azaltma_mi() is True
        and _bg.azaltma_degisken_mi() is True
        and _bg.ETKIN[1.0][1] < 2.0)
kontrol("madde 282: yoğunlaşma madde 192'nin red eşiğinin İKİ KATINDAN fazla",
        _bg.yogunlasma_madde192yi_asiyor_mu(1.0) is True
        and _bg.tek_coin_brut_payi(2.0) > 2 * _bg.MADDE_192_RED_ESIGI_BRUT)
kontrol("madde 282: ölçüt bağımlılığı yasası ÜÇ kez doğrulandı",
        _bg.yasa_kac_kez_dogrulandi() == 3
        and set(_bg.YASA) == {274, 281, 282})
kontrol("madde 282: sapma OYNAKLIKLA büyüyor (dönüş -4,7 -> -17,5 -> -47,9)",
        _bg.sapma_oynaklikla_buyuyor_mu() is True
        and _bg.YASA[282][2] < _bg.YASA[281][2] < _bg.YASA[274][2])
kontrol("madde 282: motorun ağırlığı hâlâ EŞİT (kitap birebir aynı)",
        os.environ.get("AGIRLIK", "esit") == "esit")
kontrol("madde 282: hüküm RED ve ayarın değişmediğini söylüyor",
        "RED" in _bg.hukum() and "DEGISMEDI" in _bg.hukum()
        and "gizlenmis" in _bg.hukum())
kontrol("kâr haritası madde 282'yi gizlenmiş-azaltma yasası olarak yazdı",
        "MADDE 282" in _harita
        and "GİZLENMİŞ VE DEĞİŞKEN BİR BACAK AZALTMADIR" in _harita
        and "parite gerekir" in _harita)

print("\n6ac) MADDE 283 - TEMINAT GETIRISI / BNB")
import arastirma_teminat_getirisi as _tg

kontrol("madde 283: 'atıl teminat' ekseni YOK ve hatam kayıtlı",
        _tg.atil_teminat_ekseni_var_mi() is False
        and "MARUZIYET KAPASITESI" in _tg.HATAM["neden_yanlis"]
        and "YASTIK" in _tg.HATAM["dogru_kullanim"])
kontrol("madde 283: bot sermayeyi TEMİNAT DEĞERİNDEN okuyor (hatanın sebebi)",
        "totalMarginBalance" in _tg.HATAM["neden_yanlis"]
        and "get_account_equity_usd" in _cbkaynak)
kontrol("madde 283: yastık hesabı madde 266'nın kuyruğuyla tutarlı",
        abs(_tg.GUN_ICI_KUYRUK_1X - 41.41) < 0.01
        and 40.0 < _tg.yastik(_tg.DOZ_BRUT) < 55.0
        and _tg.yastik(1.0) > _tg.yastik(1.5))
kontrol("madde 283: teminat denklemi NET = y - h*R doğru hesaplıyor",
        abs(_tg.net_puan(5.0, 0.05) - (5.0 - 0.05 * _tg.R_KITAP_NET)) < 1e-9
        and _tg.net_puan(5.0, 0.05) < 0 < _tg.net_puan(5.0, 0.01))
kontrol("madde 283: başabaş kesinti h* = y/R_kitap",
        abs(_tg.basabas_kesinti(5.0) - 5.0 / _tg.R_KITAP_NET) < 1e-12
        and 4.0 < _tg.basabas_kesinti(5.0) * 100 < 5.0)
kontrol("madde 283: bu RED bayatlamadı, GÜÇLENDİ (eşik yarıya indi)",
        _tg.esik_sertlesti_mi() is True and _tg.red_guclendi_mi() is True
        and _tg.basabas_kesinti(5.0, _tg.R_KITAP_MADDE141)
        > 2 * _tg.basabas_kesinti(5.0) * 0.9)
kontrol("madde 283: getirinin AYNI primden geldiği uyarısı kodda duruyor",
        _tg.getiri_ayni_primden_mi() is True
        and "AYNI prim" in _cbkaynak)
kontrol("madde 283: BNB kazancı madde 213'ün sabitinden türetiliyor",
        abs(_tg.PUAN_BASINA_BP - cb.PUAN_BASINA_BP) < 1e-9
        and abs(_tg.bnb_kazanci(0.10) - 0.34) < 0.01)
kontrol("madde 283: BNB'nin maliyeti ve doğrulanamayan kısmı KAYITLI",
        "notrluk ihlali" in _tg.BNB_MALIYETI
        and "URUN SARTI" in _tg.DOGRULANAMAYAN
        and "451" in _tg.DOGRULANAMAYAN)
kontrol("madde 283: teminat modu varsayılanı hâlâ usdt (ayar değişmedi)",
        cb.TEMINAT_MODU == "usdt")
kontrol("madde 283: hüküm iddiamın geri alındığını ve ayarın durduğunu söylüyor",
        "geri aliyorum" in _tg.hukum() and "DEGISMEDI" in _tg.hukum()
        and "GUCLENDI" in _tg.hukum())
kontrol("kâr haritası madde 283'ü 'atıl deme' yasası olarak yazdı",
        "MADDE 283" in _harita
        and "NE İŞ YAPTIĞINI SORMADAN" in _harita
        and "h\\* = y / R_kitap" in _harita)

print("\n6ad) MADDE 284 - REJIM BAHSININ FIYATI")
import arastirma_rejim_bahsi as _rb

kontrol("madde 284: kullanıcının sezgisi ÖLÇÜLDÜ - 25-26'da adayların HEPSİ kazanıyor",
        _rb.yeni_rejimde_kazaniyor_mu() is True
        and _rb.kac_aday_yeni_rejimde_kazaniyor() == len(_rb.KAZANC))
kontrol("madde 284: doz ölçütü ÜÇ pencerede ayrı çözüldü",
        all(set(v) == {"TAM", "22-24", "25-26"} for v in _rb.DOZ.values()))
kontrol("madde 284: kazanç ve kayıp DOZ tablosundan türetiliyor (elle değil)",
        abs(_rb.kazanc("g0.25_k0") - 20.36) < 0.05
        and abs(_rb.kayip("g0.25_k0") + 27.42) < 0.05)
kontrol("madde 284: başabaş rejim olasılığı formülü doğru",
        abs(_rb.basabas_rejim_olasiligi("g0.25_k0") - 57.4) < 0.5
        and _rb.basabas_rejim_olasiligi("g1.0_k0") > 99.0)
kontrol("madde 284: en ucuz bahis bile %50'nin ÜSTÜNDE",
        _rb.bahis_elli_ustu_mu() is True
        and _rb.en_ucuz_bahis()[0] == "g0.25_k0")
kontrol("madde 284: madde 231 SEVİYE atlaması seçiyor -> bahsin TERSİNE",
        _rb.rejim_mi_trend_mi() == "seviye"
        and _rb.madde231_tersine_mi_egiliyor() is True
        and _rb.MADDE_231["artik_seviye"] < _rb.MADDE_231["artik_trend"])
kontrol("madde 284: 25-26 kazancı KANIT BARINI geçmiyor ve aralık sıfırı kapsıyor",
        _rb.kazanc_kaniti_yeterli_mi() is False
        and _rb.kazanc_araligi_sifiri_kapsiyor_mu() is True
        and _rb.ORNEKLEME["g0.25_k0"][3] < _rb.KANIT_BARI)
kontrol("madde 284: birleşik olasılık yazı turanın altında",
        _rb.birlesik_olasilik() < 50.0)
kontrol("madde 284: RED ayakta ve şart 1'in işlevi KAYITLI",
        _rb.red_ayakta_mi() is True
        and "DEDEKTOR" in _rb.sart1_ne_ise_yarar().upper()
        and "bedeli su" in _rb.sart1_ne_ise_yarar())
kontrol("madde 284: hüküm kullanıcının sezgisini DOĞRULUYOR ama redde varıyor",
        "sezgisi KISMEN DOGRU" in _rb.hukum()
        and "red AYAKTA" in _rb.hukum()
        and "DEGISMEDI" in _rb.hukum())
kontrol("madde 284: motorun ağırlığı hâlâ varsayılan (karar uygulanmadı)",
        os.environ.get("AGIRLIK", "esit") == "esit")
kontrol("kâr haritası madde 284'ü bahis-fiyatlama yasası olarak yazdı",
        "MADDE 284" in _harita
        and "REJİM BAHSİ DEDEKTÖRÜDÜR" in _harita
        and "BAHSİ FİYATLA" in _harita)

print("\n6ae) MADDE 285 - ASGARI SAPTANABILIR ETKI")
import arastirma_asgari_etki as _ae

kontrol("madde 285: madde 244'ün adayı YENİDEN ÜRETİLDİ (Sharpe ve korelasyon)",
        _ae.yeniden_uretim_tuttu_mu() is True)
kontrol("madde 285: harman tam örnekte VE 22-24'te iyileşiyor",
        _ae.erken_ve_tam_iyilesiyor_mu(0.10) is True
        and _ae.erken_ve_tam_iyilesiyor_mu(0.20) is True)
kontrol("madde 285: şart 1 kaybı YUVARLAMA mertebesinde (-0,012)",
        _ae.sart1_yuvarlama_mi(0.10) is True)
kontrol("madde 285: DÜŞÜŞ İYİLEŞİYOR - reddedilenlerin TERSİ imza",
        _ae.dusus_iyilesiyor_mu(0.10) is True
        and _ae.dusus_iyilesiyor_mu(0.20) is True)
kontrol("madde 285: şart 4'ün gerekçesi madde 276'nın doz kararıyla geçersiz",
        _ae.sart4_gerekcesi_gecersiz_mi() is True
        and _ae.MADDE_276_DOZ >= _ae.SART4_GEREKEN)
kontrol("madde 285: bahis DÜŞÜK prim rejimine ve madde 231 bu yönü destekliyor",
        _ae.bahis_yonu(0.10) == "dusuk prim rejimi"
        and _ae.madde231_bu_yonu_destekliyor_mu() is True)
kontrol("madde 285: bahis madde 282'nin bahsinden UCUZ (%25,4 vs %57,4)",
        _ae.en_ucuz_bahis_mi() is True
        and _ae.bahis_fiyati(0.10) < 30.0)
kontrol("madde 285: TAM ÖRNEKTE doz ölçütü POZİTİF ve İÇ OPTİMUM",
        _ae.doz_olcutu_pozitif_mi() is True
        and _ae.doz_ic_optimum_mu() is True)
kontrol("madde 285: brüt İYİLEŞİYOR (reddedilenlerde çöküyordu)",
        _ae.brut_iyilesiyor_mu() is True)
kontrol("madde 285: kanıt barı GEÇİLMİYOR ve madde 244 ile TUTARLI",
        _ae.kanit_bari_gecildi_mi() is False
        and abs(_ae.DOZ[0.20][2] - _ae.MADDE_244_BOOTSTRAP[0]) < 2.0)
kontrol("madde 285: GÜÇ boşluğu bir ON YIL (14,2 yıl vs 4,1)",
        _ae.guc_boslugu_on_yil_mi() is True
        and _ae.gereken_yil(0.20) > 10.0)
kontrol("madde 285: ASE yasası - adayın etkisi ASE'nin ALTINDA",
        _ae.ase_altinda_mi(_ae.DOZ[0.20][2]) is True
        and _ae.proje_guc_sinirli_mi() is True
        and _ae.ASE_PUAN > 10.0)
kontrol("madde 285: karar meşru olarak KULLANICIYA ait ve ayar DEĞİŞMEDİ",
        _ae.karar_kullaniciya_mi_ait() is True
        and "DEGISMEDI" in _ae.hukum()
        and "KARARLASTIRILAMAZ" in _ae.hukum())
kontrol("madde 285: motorun sinyali hâlâ funding (karar uygulanmadı)",
        abs(cb.FUNDING_WINDOW_HOURS - 48.0) < 1e-9)
kontrol("kâr haritası madde 285'i güç-sınırı yasası olarak yazdı",
        "MADDE 285" in _harita
        and "GÜÇ SINIRLI" in _harita
        and "GÜÇ BÜTÇESİNİ" in _harita)

print("\n6af) MADDE 286 - CANLI KAPI + ASE ON FILTRESI")
import arastirma_canli_kapi as _ck286
import karar_kurali as _kk286
import subprocess as _sp

kontrol("madde 286: kusur bulundu ve DÜZELTİLDİ (kod 3 = ÖLÇÜLEMEDİ)",
        _ck286.kusur_bulundu_mu() is True
        and _ck286.kusur_duzeltildi_mi() is True)
kontrol("madde 286: eski kod verdiktle AYNIYDI (1 = İNCELE)",
        _ck286.eski_kod_verdiktle_ayni_miydi() is True)
kontrol("madde 286: 'ölçemedim' kodu verdikt kodlarından AYRI",
        _ck286.olcemedim_ile_supheli_ayri_mi() is True
        and 3 not in (0, 1, 2))
kontrol("madde 286: carry_izleme anahtar yokken GERÇEKTEN 3 döndürüyor",
        _sp.run([sys.executable, os.path.join(R, "carry_izleme.py"), "--gun", "14"],
                capture_output=True, timeout=120,
                env={k: v for k, v in os.environ.items()
                     if k not in ("BINANCE_API_KEY", "BINANCE_API_SECRET")},
                cwd=R).returncode == 3)
kontrol("madde 286: carry_izleme ÖLÇÜLEMEDİ mesajını yazıyor",
        "ÖLÇÜLEMEDİ" in _sp.run(
            [sys.executable, os.path.join(R, "carry_izleme.py"), "--gun", "14"],
            capture_output=True, timeout=120, text=True,
            env={k: v for k, v in os.environ.items()
                 if k not in ("BINANCE_API_KEY", "BINANCE_API_SECRET")},
            cwd=R).stdout)
kontrol("madde 286: carry_preflight --yerel hâlâ 0, anahtarsız 1",
        _sp.run([sys.executable, os.path.join(R, "carry_preflight.py"), "--yerel"],
                capture_output=True, timeout=180, cwd=R).returncode == 0)
kontrol("madde 286: iki başarısızlık yolu da sınandı",
        _ck286.iki_yol_da_sinandi_mi() is True)
kontrol("madde 286: yalnız EN KRİTİK araç kusurluydu, diğerleri temiz",
        _ck286.yalniz_en_kritik_arac_mi_kusurluydu() is True
        and _ck286.aile_kac_arac_temiz() == 5)
kontrol("madde 286: kendi ÖLÇÜM hatam kayıtlı",
        _ck286.olcum_hatam_kayitli_mi() is True)
kontrol("madde 286: ASE ön filtresi karar_kurali'nda ve doğru",
        hasattr(_kk286, "ASE_PUAN") and hasattr(_kk286, "tur_degerli_mi")
        and _ck286.on_filtre_dogru_mu() is True
        and abs(_kk286.ASE_PUAN - _ck286.ASE_PUAN) < 1e-9)
kontrol("madde 286: ön filtre ASE altındaki etkiyi 'hüküm veremez' sayıyor",
        _kk286.tur_degerli_mi(7.22)["saptanabilir"] is False
        and _kk286.tur_degerli_mi(20.0)["saptanabilir"] is True
        and _kk286.gereken_ufuk_yil(7.22) > 10.0)
kontrol("madde 286: ön filtre son turları elerdi",
        _ck286.on_filtre_son_turlari_elerdi_mi() is True)
kontrol("madde 286: canlıya çıkış belgesi kod 3'ü yazdı",
        "MADDE 286" in _ham and "ÖLÇÜLEMEDİ" in _ham
        and "verdikt DEĞİL" in _ham)
kontrol("madde 286: strateji ayarı DEĞİŞMEDİ",
        _ck286.ayar_degismedi_mi() is True
        and abs(cb.GROSS_EXPOSURE - 1.0) < 1e-9)
kontrol("kâr haritası madde 286'yı başarısızlık-yolu yasası olarak yazdı",
        "MADDE 286" in _harita
        and "ÖLÇÜMÜN BAŞARISIZ OLDUĞU YOLDUR" in _harita)

print("\n6ag) MADDE 287 - PRIM-OLCEKLI BRUT")
import arastirma_prim_brut as _pb

kontrol("madde 287: denetimin kendi notu - iki taban (kontrol/plasebo) karıştırılmıyor",
        _pb.taban_karistirilmadi_mi() is True)
kontrol("madde 287: madde 239'un adayı YENİDEN ÜRETİLDİ",
        _pb.yeniden_uretim_tuttu_mu() is True)
kontrol("madde 287: PLASEBO kontrolün ALTINDA - etki DOZ değil ZAMANLAMA",
        _pb.plasebo_sifir_mi() is True
        and _pb.GUNLUK["plasebo"][5] < _pb.GUNLUK["kontrol"][5])
kontrol("madde 287: adayın DÜŞÜŞÜ İYİLEŞİYOR",
        _pb.dusus_iyilesiyor_mu() is True
        and _pb.GUNLUK["aday"][4] < _pb.GUNLUK["kontrol"][4])
kontrol("madde 287: doz ölçütü (madde 281'in son kapısı) GEÇİLDİ",
        _pb.doz_olcutu_gecti_mi() is True
        and _pb.DOZ["aday"][2] > 30.0
        and _pb.DOZ["plasebo"][2] < 1.0)
kontrol("madde 287: KANIT BARI doz ölçütünde GEÇİLDİ (%90,7 > %80)",
        _pb.kanit_bari_gecti_mi() is True
        and _pb.BOOTSTRAP["aday"][4] > _pb.KANIT_BARI)
kontrol("madde 287: plasebonun bootstrap'ı YAZI-TURA (kontrol testi çalışıyor)",
        45.0 < _pb.BOOTSTRAP["plasebo"][4] < 55.0)
kontrol("madde 287: madde 239 barı BAŞKA ölçütte ölçmüştü (eşit-risk %79,0)",
        abs(_pb.MADDE_239_ESITRISK_P - 79.0) < 0.1
        and "DOZ olcutunu son kapi" in _pb.bar_hangi_olcutte_gecilmedi())
kontrol("madde 287: bahis fiyatı %5'in ALTINDA ve kayıp bacağı YOK",
        _pb.bahis_fiyati() < 5.0
        and _pb.kayip_bacagi_var_mi() is False)
kontrol("madde 287: etki ASE'nin 2 KATINDAN fazla -> KARARLAŞTIRILABİLİR",
        _pb.kararlastirilabilir_mi() is True
        and _pb.ase_kac_kati() > 2.0
        and _kk286.saptanabilir_mi(_pb.DOZ["aday"][2]) is True)
kontrol("madde 287: PLATO doğrulandı ve kayıtlı nokta TEPE DEĞİL",
        _pb.plato_mu() is True
        and _pb.kayitli_nokta_tepe_mi() is False
        and len(_pb.PLATO) == 6)
kontrol("madde 287: şart 1 GEÇMİYOR ve kural GEVŞETİLMEDİ",
        _pb.sart1_gecti_mi() is False
        and _pb.kural_gevsetildi_mi() is False
        and "madde 212" in _pb.KURAL_GEVSETILMEDI)
kontrol("madde 287: beş dürüst risk KAYITLI (şart 1 ihlali dahil)",
        len(_pb.RISKLER) == 5
        and any("sart 1 ihlali GERCEK" in r for r in _pb.RISKLER))
kontrol("madde 287: madde 285'in adayından HER ölçütte güçlü",
        _pb.madde285_adayindan_guclu_mu() is True)
kontrol("madde 287: motorun brüt priminin varsayılanı HÂLÂ KAPALI",
        'BRUT_PRIM=float(os.environ.get("BRUT_PRIM","0"))' in _cbg33)
kontrol("kâr haritası madde 287'yi sicil-denetimi yasası olarak yazdı",
        "MADDE 287" in _harita
        and "YENİDEN OKUNUR" in _harita
        and "HAVUZLANAMAZ" in _harita)

print("\n6ah) MADDE 288 - PRIM DOZU, KURALIN PLASEBOYU GECIRMESI, ADAYA AIT ASE")
import arastirma_prim_doz as _pd288
import karar_kurali as _kk288
import carry_bot as _cb288

kontrol("madde 288: kisayol KONTROLDE tuttu (ve bu yetmedi)",
        _pd288.kisayol_kontrolde_tuttu_mu() is True)
kontrol("madde 288: ayni kisayol ADAYDA 2 kattan fazla sisti",
        _pd288.kisayol_adayda_sisti_mi() is True)
kontrol("madde 288: ASE gozlemleri MONOTON DEGIL (sabit ASE yanlislandi)",
        _pd288.ase_monoton_mu() is False
        and _kk288.ase_monoton_mu() is False)
kontrol("madde 288: sabit ASE secilen adayi turun basinda elerdi",
        _pd288.sabit_ase_turu_oldururdu_mu() is True)
kontrol("madde 288: karar_kurali ADAYA AIT ASE hesabini sunuyor",
        hasattr(_kk288, "ase_puan_adaydan")
        and abs(_kk288.ase_puan_adaydan(10.0) - 8.416) < 1e-6)
kontrol("madde 288: tur_degerli_mi sigma VERILMEDIKCE hukum vermiyor",
        "YANLISLANDI" in _kk288.tur_degerli_mi(5.0)["ase_kaynagi"]
        and "uyari" in _kk288.tur_degerli_mi(5.0))
kontrol("madde 288: sigma verilince karar ADAYA ozel",
        _kk288.tur_degerli_mi(12.15, sigma_boot=8.08)["saptanabilir"] is True
        and _kk288.tur_degerli_mi(1.32, sigma_boot=2.44)["saptanabilir"] is False)
kontrol("madde 285'in eski cagrilari KORUNDU (geriye donuk uyum)",
        _kk288.tur_degerli_mi(7.22)["saptanabilir"] is False
        and _kk288.tur_degerli_mi(20.0)["saptanabilir"] is True)
kontrol("madde 288: KARISTIRILMIS PLASEBO dort sarti GECIYOR (ucuncu yasa)",
        _pd288.kural_plaseboyu_geciriyor_mu() is True)
kontrol("madde 288: ama doz olcutu + bootstrap plaseboyu AYIRIYOR",
        _pd288.bootstrap_plaseboyu_geciriyor_mu() is False)
kontrol("madde 288: zamanda ters plasebo kontrolun ALTINDA",
        _pd288.ters_plasebo_kontrolun_altinda_mi() is True)
kontrol("madde 288: doz-yaniti MONOTON (coklu bakisa karsi savunma)",
        _pd288.doz_yaniti_monoton_mu() is True)
kontrol("madde 288: gecen band kapali (iki kenar da dusuyor)",
        _pd288.band_kapali_mi() is True)
kontrol("madde 288: secilen hucre bandin ORTASI (en iyisi degil gerekcesi)",
        _pd288.secilen_bandin_ortasi_mi() is True)
kontrol("madde 288: secilen nokta dort sarti geciyor",
        _pd288.dort_sart_gecti_mi() is True)
kontrol("madde 288: kanit bari doz olcutunde GECILDI",
        _pd288.kanit_bari_gecti_mi() is True)
kontrol("madde 288: rejim bahsi DEGIL (iki bacak da arti)",
        _pd288.bahis_mi() is False)
kontrol("madde 288: sart-1 gecisi GURULTU olarak KAYITLI",
        _pd288.sart1_gurultu_mu() is True)
kontrol("madde 288: bu dozda KALDIRAC KARARI yok (ort carpan 1,005)",
        _pd288.kaldirac_karari_mi() is False)
kontrol("madde 288: bot knobunun VARSAYILANI KAPALI",
        _pd288.varsayilan_kapali_mi() is True
        and _cb288.PRIM_E == 0.0)
kontrol("madde 288: prim carpani KAPALIYKEN tam olarak 1,0",
        _cb288.prim_carpani() == 1.0)
kontrol("madde 288: gecmis yoksa carpan 1,0 (isinma zararsiz)",
        _cb288.prim_carpani("/tmp/__yok_288__.csv") == 1.0)
kontrol("madde 288: prim_olc kesitsel p90-p10 doner",
        abs(_cb288.prim_olc(_cb288.pd.Series(
            {"a": 0.1, "b": 0.2, "c": 0.3, "d": 0.4, "e": 0.5, "f": 0.6}))
            - 0.4) < 1e-9)
kontrol("madde 288: az sembolde prim_olc NaN (veri eksikligi karar vermez)",
        _cb288.prim_olc(_cb288.pd.Series({"a": 0.1})) != _cb288.prim_olc(
            _cb288.pd.Series({"a": 0.1})))
kontrol("madde 288: bot kancasi TEK yerde ve olcek uzerinden",
        _kaynak.count("olcek *= prim_carpani()") == 1)
kontrol("madde 288: gerekli_kaldirac prim tavanini paya katiyor",
        "olcek_max *= PRIM_UST" in _kaynak)
kontrol("madde 288: ref varsayilani bandin ortasi (150)",
        _cb288.PRIM_REF_GUN == 150)
kontrol("madde 288: belge acilis komutunu TEK SATIR olarak veriyor",
        "CARRY_PRIM_E=0.10" in _ham and "~75 g" in _ham.replace(
            "ü", "u").replace("İ", "I"))
kontrol("kâr haritası madde 288'i kural-plaseboyu-geciriyor yasası olarak yazdı",
        "Madde 288" in _harita and "ELEME cümlesidir" in _harita)
kontrol("madde 288: motorun brut priminin varsayilani HALA KAPALI",
        'BRUT_PRIM=float(os.environ.get("BRUT_PRIM","0"))' in _cbg33)

print("\n6ai) MADDE 289 - KURALIN GUC EGRISI")
import arastirma_kural_gucu as _kg289

kontrol("madde 289: simulasyon MOTORLA dogrulandi (null yanlis gecme)",
        _kg289.simulasyon_motorda_dogrulandi_mi() is True)
kontrol("madde 289: motorda olculen yanlis gecme orani %20 (2/10)",
        abs(_kg289.yanlis_gecme_orani_motorda() - 20.0) < 1e-6)
kontrol("madde 289: null'da sart 1 iki yazi-turaya yakin (%25)",
        _kg289.sart1_iki_yazi_tura_mi() is True)
kontrol("madde 289: GERCEK bir +1,33 puanlik kazanc yarisindan cok ELENIYOR",
        _kg289.gercek_kazanc_eleniyor_mu() is True)
kontrol("madde 289: izleme hatasi buyurken guc HER delta'da dusuyor",
        _kg289.izleme_buyurken_guc_dusuyor_mu() is True)
kontrol("madde 289: gecersiz simulasyon kolu YAYIMLANMADI",
        _kg289.hatam_yayimlanmadi_mi() is True
        and "BOZULMUS" in _kg289.HATAM["neden_gecersiz"].upper())
kontrol("madde 289: cesitlendiricide baglayici sart SART 4",
        _kg289.cesitlendiricide_baglayici_sart_dort_mu() is True)
kontrol("madde 289: esik KITABIN KENDI Sharpe'i",
        _kg289.esik_kitabin_sharpe_i_mi() is True
        and abs(_kg289.KONTROL_SHARPE - 2.940) < 1e-9)
kontrol("madde 289: negatif korelasyon HICBIR SEY kazandirmiyor",
        _kg289.korelasyon_yardim_ediyor_mu() is False)
kontrol("madde 289: sart 4 ile doz olcutu ZIT yon gosteriyor",
        _kg289.iki_kapi_ters_mi() is True)
kontrol("madde 289: celiskinin sirasi KAYITLI (sart 4, madde 276'dan ONCE)",
        "ONCE" in _kg289.CELISKI["sira"].upper()
        and "276" in _kg289.CELISKI["tolerans"])
kontrol("madde 289: kural DEGISTIRILMEDI (madde 212'nin deligi)",
        _kg289.kural_degistirilmedi_mi() is True)
kontrol("madde 289: sabit brutte bedavaya yakin bir takas VAR",
        _kg289.sabit_brutte_bedavaya_yakin_var_mi() is True)
kontrol("madde 289: dusus kesmenin kuru dilimin Sharpe'iyla DEGISIYOR",
        _kg289.takas_kuru(2.50, -0.50) < 0.5
        and _kg289.takas_kuru(1.50, -0.50) > 2.5)
kontrol("madde 289: arama sartnamesi Sharpe esigi koyuyor",
        _kg289.SARTNAME["tek_basina_sharpe_min"] >= 2.5
        and _kg289.SARTNAME["korelasyon_max"] <= 0.0)
kontrol("madde 289: SENTETIK uyarisi kayitli (boyle bir kitap BULUNMADI)",
        "BULUNMADI" in _kg289.SIMULASYON_UYARISI)
kontrol("kâr haritası madde 289'u sartname yasası olarak yazdı",
        "Madde 289" in _harita and "sıfır fiyatlıyor" in _harita)

print("\n6aj) MADDE 290 - KITAP TARAMASI VE MADDE 214'UN DUZELTMESI")
import arastirma_kitap_taramasi as _kt290

kontrol("madde 290: sartnameyi tutan kitap YOK (rho<=0 ekseni BOS)",
        _kt290.sartnameyi_tutan_var_mi() is False)
kontrol("madde 290: karli kitaplarin en dusuk rho'su +0,635",
        abs(_kt290.en_dusuk_rho_karli_kitap() - 0.635) < 1e-9)
kontrol("madde 290: madde 288'in adayi CESITLENDIRME DEGIL (rho 0,997)",
        _kt290.madde288_adayi_cesitlendirme_mi() is False)
kontrol("madde 290: en guclu aday YALNIZ sart 4'ten dusuyor",
        _kt290.en_guclu_aday_sart4ten_mi_dusuyor() is True)
kontrol("madde 290: kuralin hukmu KANITLA TERS korelasyonlu",
        _kt290.kural_hukmu_kanitla_ters_mi() is True)
kontrol("madde 290: kurali GECEN aday kanit barini GECEMIYOR",
        _kt290.gecen_aday_bari_gecemiyor_mu() is True)
kontrol("madde 290: kuraldan DUSEN aday kanit barini GECIYOR",
        _kt290.dusen_aday_bari_geciyor_mu() is True)
kontrol("madde 290: iki aday da rejim bahsi DEGIL",
        all(_kt290.bahis_mi(a) is False for a in _kt290.BAHIS))
kontrol("madde 290: oynaklik SATIN ALAN aday 2 gunluk ufuk",
        _kt290.oynaklik_satin_alan_hangisi() == "2 gunluk ufuk")
kontrol("madde 290: sabit brut siralamayi TERSINE ceviriyor",
        _kt290.sabit_brut_siralamayi_ters_mi_ceviriyor() is True)
kontrol("madde 290: hasat karin TAMAMI DEGIL (madde 214 duzeltildi)",
        _kt290.hasat_karin_tamami_mi() is False)
kontrol("madde 290: hasat KAPALIYKEN ham fiyat KAZANDIRIYOR",
        _kt290.hasatsizda_fiyat_kazandiriyor_mu() is True)
kontrol("madde 290: hasadin payi karin ~%17'si",
        14.0 < _kt290.hasadin_payi() < 20.0)
kontrol("madde 290: hasatsiz kitap hala KARLI (+%93,4 / Sharpe 2,33)",
        _kt290.HASATSIZ[0] > 90.0 and _kt290.HASATSIZ[1] > 2.2)
kontrol("madde 290: madde 214'un SECICI kismi AYAKTA",
        "SECICI" in _kt290.MADDE_214_AYAKTA)
kontrol("madde 290: SHORT funding siralamasinin degeri olculdu",
        _kt290.SHORT_SECICI["cagr"] > 25.0)
kontrol("madde 290: uc etiketleme hatasi KAYITLI ve yayimlanmadi",
        len(_kt290.ETIKET_HATALARIM) == 3
        and _kt290.etiket_hatalari_yayimlanmadi_mi() is True)
kontrol("madde 290: knob yasasi kayitli (0 = ayri rejim)",
        "KANITLAMAZ" in _kt290.ETIKET_YASASI)
kontrol("carry_bot: madde 214'un 'TAMAMI' iddiasi YERINDE DUZELTILDI",
        "MADDE 290" in _kaynak and "MUHASEBE ARTEFAKTI" in _kaynak
        and "+64,9" in _kaynak)
kontrol("kâr haritası madde 290'i muhasebe-artefakti yasası olarak yazdı",
        "Madde 290" in _harita and "MUHASEBE ARTEFAKTIDIR" in _harita)

print("\n6ak) MADDE 291 - ICRA VARSAYIMLARI 1 YILLIK UFUKTA")
import arastirma_ufuk_dogrulama as _uf291

kontrol("madde 291: arac madde 266'yi KENDI penceresinde yeniden uretti",
        _uf291.arac_madde266yi_uretti_mi() is True)
kontrol("madde 291: kapital konvansiyonu hatam KAYITLI",
        _uf291.kapital_hatam_kayitli_mi() is True)
kontrol("madde 291: rejim ONEMLI DEGIL (bant 1,16-1,35)",
        _uf291.rejim_onemli_mi() is False)
kontrol("madde 291: FTX cokusu ayi AYKIRI DEGIL",
        _uf291.ftx_ayi_aykiri_mi() is False)
kontrol("madde 291: buyutme pencere uzunlugunda MONOTON DEGIL (U)",
        _uf291.pencere_monoton_mu() is False
        and _uf291.ekstrapole_edilebilir_mi() is False)
kontrol("madde 291: U'nun dibi 3 ay",
        _uf291.u_biciminin_dibi() == "3 ay")
kontrol("madde 291: 1 yillik buyutme 2-3 aylik olandan BUYUK",
        _uf291.PENCERE["12 ay"][2] > _uf291.PENCERE["3 ay"][2])
kontrol("madde 291: madde 276 IHTIYATLI tarafta (guvenli yon)",
        _uf291.madde276_ihtiyatli_mi() is True)
kontrol("madde 291: madde 276'nin p90'i ~%32 ihtiyatli",
        28.0 < _uf291.madde276_p90_kac_yuzde_ihtiyatli() < 38.0)
kontrol("madde 291: doz kalibrasyonu 1 YILLIK ufukta DOGRULANDI",
        _uf291.doz_kalibrasyonu_dogrulandi_mi() is True)
kontrol("madde 291: tur ortasindaki duyurum YANLIS olarak kayitli",
        _uf291.duyurum_yanlis_mi() is True
        and "YONUNU" in _uf291.YANLIS_DUYURUM["ders"].upper())
kontrol("madde 291: TEK YIL belirsizligi kayitli",
        _uf291.tek_yil_uyarisi_kayitli_mi() is True)
kontrol("madde 291: surekli panel gercekten 365 gun",
        abs(_uf291.PANEL["gun"] - 365.0) < 1.0
        and _uf291.PANEL["bar"] == 525600)
kontrol("madde 291: madde 276'nin kullandigi sayilar DEGISMEDI",
        abs(_uf291.MADDE_276["medyan"] - 1.488) < 1e-9
        and abs(_uf291.MADDE_276["p90"] - 2.722) < 1e-9)
kontrol("kâr haritası madde 291'i ufuk yasası olarak yazdı",
        "Madde 291" in _harita and "VERİLDİĞİ ufukta ölç" in _harita)

print("\n6al) MADDE 292 - EMIR YASAM DONGUSU: TP KONMA DEFTERI")
import arastirma_emir_yasam as _ey292
import tempfile as _tf292, time as _tm292

kontrol("madde 292: dort hipotezin dordu de NON-BULGU olarak kayitli",
        _ey292.kac_hipotez_savunulmus_cikti() == 4
        and _ey292.non_bulgular_yayimlanmadi_mi() is True)
kontrol("madde 292: motorun da harmanlanmis giris tuttugu kayitli",
        _ey292.motor_de_harmanli_giris_mi() is True)
kontrol("madde 292: motor GERCEKTEN harmanlanmis giris tutuyor (g33.py)",
        "giris[k]=(abs(poz[k])*e+dw*f)/(abs(poz[k])+dw)" in _cbg33)
kontrol("madde 292: bulgu hasada dokunuyor ve yanlis teshis kayitli",
        _ey292.bulgu_hasada_mi_dokunuyor() is True
        and _ey292.yanlis_teshis_kayitli_mi() is True)
kontrol("madde 292: retry ve madde 286 ayrimi uygulandi",
        _ey292.retry_var_mi() is True
        and _ey292.madde286_ayrimi_uygulandi_mi() is True)
kontrol("madde 292: carry_bot TP KONMA defterini sunuyor",
        hasattr(cb, "TP_KURULUM_DOSYA") and hasattr(cb, "tp_kurulum_oku")
        and hasattr(cb, "_tp_kurulum_kaydet"))
kontrol("madde 292: kar_al_kur ERROR raporunda hasadin fiyati var",
        "KÂR AL EMRİ KONULAMADI" in _kaynak and "+18,9" in _kaynak)
kontrol("madde 292: kar_al_kur tek seferlik yeniden deneme yapiyor",
        "TEK SEFERLİK YENİDEN DENEME" in _kaynak)
_d292 = _tf292.mkdtemp(); _y292 = _d292 + "/k.csv"
_n292 = _tm292.time()
with open(_y292, "w", encoding="utf-8") as _fh292:
    _fh292.write("%.0f,50,50,0\n" % (_n292 - 3600))
    _fh292.write("%.0f,-1,0,-1\n" % (_n292 - 5400))
    _fh292.write("%.0f,50,42,8\n" % (_n292 - 7200))
    _fh292.write("bozuk satir\n")
    _fh292.write("%.0f,50,50,0\n" % (_n292 - 40 * 86400))
_r292 = cb.tp_kurulum_oku(_y292, gun=30)
kontrol("madde 292: defter okuma - pencere, bozuk satir, olculemeyen tur",
        _r292["tur"] == 2 and _r292["hedeflenen"] == 100
        and _r292["kurulan"] == 92 and _r292["olculemedi"] == 1)
kontrol("madde 292: olculemeyen tur orani BOZMUYOR (oran <= 1)",
        0.0 < _r292["oran"] <= 1.0
        and abs(_r292["oran"] - 0.92) < 1e-9)
kontrol("madde 292: bos defter nan dondurur (sifir DEGIL)",
        cb.tp_kurulum_oku(_d292 + "/yok.csv")["oran"] != cb.tp_kurulum_oku(
            _d292 + "/yok.csv")["oran"])
kontrol("madde 292: izleme ONCE konma oranina bakiyor",
        "TP KONMA oranı" in _izl and "_kurulum_bozuk" in _izl)
kontrol("madde 292: izleme icra arizasini PIYASA bulgusundan AYIRIYOR",
        "İCRA arızasıdır" in _izl and "Strateji şüpheli DEĞİL" in _izl)
kontrol("madde 292: izleme 'kar motoru' suclamasini ancak konma >=%95 ise yapiyor",
        "konma oranı ≥%95" in _izl)
kontrol("madde 292: konma esigi %95",
        abs(_ey292.KONMA_ESIGI - 0.95) < 1e-9 and "0.95" in _izl)
kontrol("kâr haritası madde 292'yi canli-kar yasası olarak yazdı",
        "Madde 292" in _harita and "SESSİZCE para kaybeder" in _harita)

print("\n6am) MADDE 293 - COK DILIMLI HARMAN VE SERMAYE TABANI")
import arastirma_cok_dilim as _cd293

kontrol("madde 293: merkez HER HAM EKSENDE kontrolden iyi",
        _cd293.merkez_her_eksende_iyi_mi() is True)
kontrol("madde 293: on kayitli kural bedelini odedi (maksimumun ALTINDA)",
        _cd293.merkez_maksimumun_altinda_mi() is True)
kontrol("madde 293: en yuksek dozlar SART 4'ten dusuyor (madde 289, 3. kez)",
        _cd293.en_iyiler_sart4ten_mi_dusuyor() is True)
kontrol("madde 293: kanit bari GECILDI (P %96,0)",
        _cd293.merkez_bari_gecti_mi() is True)
kontrol("madde 293: p5 ARTIDA - projede ilk",
        _cd293.p5_artida_mi() is True)
kontrol("madde 293: rejim bahsi DEGIL",
        _cd293.merkez_bahis_mi() is False)
kontrol("madde 293: sermaye tabani tablosu 1/agirlik ile tutuyor",
        _cd293.sermaye_tabani_dogru_mu() is True)
kontrol("madde 293: merkez 20 KAT sermaye istiyor",
        abs(_cd293.merkez_kac_kat_sermaye_istiyor() - 20.0) < 1e-6)
kontrol("madde 293: 15.000 $'da UYGULANAMAZ",
        _cd293.merkez_uygulanabilir_mi(15000.0) is False)
kontrol("madde 293: 37.500 $'da uygulanabilir",
        _cd293.merkez_uygulanabilir_mi(37500.0) is True)
kontrol("madde 293: sermaye tabani projenin KENDI fonksiyonuyla tutuyor",
        abs(cb.bakiye_yeterli_mi(1875.0, cb.N_LEGS, 1.0)[1] - 10.0) < 1e-9
        and abs(cb.bakiye_yeterli_mi(15000.0, cb.N_LEGS, 1.0)[1] - 80.0) < 1e-9)
kontrol("madde 293: madde 204 sonucu kayitli (dilim SESSIZCE var olmaz)",
        "SESSIZCE var olmaz" in _cd293.MADDE_204_SONUCU)
kontrol("madde 293: kisitli secim kurali KENDINI CURUTTU",
        _cd293.kisit_kurali_curudu_mu() is True)
kontrol("madde 293: kural sonradan DEGISTIRILMEDI (madde 212)",
        _cd293.kural_sonradan_degistirilmedi_mi() is True)
kontrol("madde 293: iki dilim daha uygulanabilir AMA kaniti daha zayif",
        _cd293.iki_dilim_daha_mi_uygulanabilir() is True
        and _cd293.iki_dilim_kaniti_daha_mi_zayif() is True)
kontrol("madde 293: plasebo adayi IYILESTIRDI (plasebo GECERSIZ)",
        _cd293.plasebo_adayi_iyilestirdi_mi() is True)
kontrol("madde 293: uc hatam da kayitli (ne + ders)",
        _cd293.uc_hatam_kayitli_mi() is True)
kontrol("madde 293: ayar DEGISMEDI",
        _cd293.ayar_degisti_mi() is False)
kontrol("kâr haritası madde 293'ü sermaye-tabanı yasası olarak yazdı",
        "Madde 293" in _harita and "1/AĞIRLIK İLE BÜYÜR" in _harita)

print("\n6an) MADDE 294 - KUCUK SERMAYE YAPILANDIRMASI")
import arastirma_kucuk_sermaye as _ks294

kontrol("madde 294: 1.000 $'da standart kitap CALISMAZ",
        _ks294.kontrol_1000de_calisir_mi() is False)
kontrol("madde 294: 2.000 $'da standart kitap calisir",
        _ks294.kontrol_2000de_calisir_mi() is True)
kontrol("madde 294: teknik taban formulu kontrolun 1.875 $'ini uretiyor",
        _ks294.teknik_taban_dogru_mu() is True)
kontrol("madde 294: taban formulu botun KENDI fonksiyonuyla ayni",
        abs(_ks294.bacak_usd(1875.0, 15, 5, 0.20)
            - cb.bakiye_yeterli_mi(1875.0, cb.N_LEGS, 1.0)[1]) < 1e-9)
kontrol("madde 294: oneri 1.000 $'da CALISIR",
        _ks294.oneri_1000de_calisir_mi() is True)
kontrol("madde 294: oneri 1.000 $'da EN BUYUK bacagi veriyor",
        _ks294.oneri_en_buyuk_bacak_mi(1000.0) is True)
kontrol("madde 294: oneri standart kitabin UC KATI bacak veriyor",
        abs(_ks294.oneri_ayni_bacagi_kac_kat_erken_veriyor() - 3.0) < 1e-6)
kontrol("madde 294: onerinin yapisal maliyeti kucuk (<10 puan)",
        _ks294.onerinin_dozu_yapisal_olarak_kucuk_mu() is True)
kontrol("madde 294: onerinin getirisi kontrole YAKIN",
        _ks294.onerinin_getirisi_kontrole_yakin_mi() is True)
kontrol("madde 294: EVREN maliyeti en kotu YAPISAL secimden buyuk",
        _ks294.evren_maliyeti_yapisaldan_buyuk_mu() is True)
kontrol("madde 294: madde 176 GUNCEL yapilandirmada dogrulandi",
        _ks294.madde176_dogrulandi_mi() is True)
kontrol("madde 294: evren maliyeti %1 basina 1,9-3,9 puan",
        all(1.5 < v < 4.5 for v in _ks294.evren_puan_basina()))
kontrol("madde 294: esit riskte EN AZ kaybeden (15x2) ONERILMEDI",
        _ks294.en_az_kaybeden_onerilmedi_mi() is True)
kontrol("madde 294: 15x2'nin gun ici karsiligi -%30 toleransini ASIYOR",
        _ks294.tolerans_asimi(24.75) > 30.0)
kontrol("madde 294: onerinin gun ici karsiligi tolerans ICINDE",
        _ks294.tolerans_asimi(16.12) < 30.0)
kontrol("madde 294: varsayilana donus esigi ~28.125 $ ve adim tavanini geciyor",
        _ks294.donus_esigi_dogru_mu() is True
        and abs(_ks294.VARSAYILANA_DONUS_ESIGI - 28125.0) < 1.0)
kontrol("madde 294: ilk donus-esigi hatam KAYITLI",
        "3.750" in _ks294.ilk_donus_esigi_hatam())
kontrol("madde 294: cerceve notu kayitli (kontrol MEVCUT DEGIL)",
        "MEVCUT DEGIL" in _ks294.CERCEVE_NOTU)
kontrol("madde 294: adim ankralari botun docstring'iyle ayni",
        "BTC ~100$" in _kaynak.replace("BTC ~100 $", "BTC ~100$")
        or "BTC ~100$" in _kaynak or "BTC ~100 $" in _kaynak)
kontrol("madde 294: varsayilan DILIM sayisi DEGISMEDI (15)",
        cb.N_DILIM == 15)
kontrol("kâr haritası madde 294'ü bacak-buyuklugu yasası olarak yazdı",
        "Madde 294" in _harita and "BACAK BÜYÜKLÜĞÜDÜR" in _harita)

print("\n6ao) MADDE 295 - GERCEK EVREN ESIGI")
import arastirma_evren_esigi as _ee295

kontrol("madde 295: SEMBOL_HARIC paritesi iki fazda BIREBIR",
        _ee295.parite_birebir_mi() is True)
kontrol("madde 295: motorda SEMBOL_HARIC var ve BOS birakilirsa etkisiz",
        "_HARIC=os.environ.get('SEMBOL_HARIC','').strip()" in _cbg33
        and "if _HARIC:" in _cbg33)
kontrol("madde 295: eleme BASAMAKLI (16->20 ucurumu 10->16'dan cok buyuk)",
        _ee295.eleme_basamakli_mi() is True)
kontrol("madde 295: QNT'nin katkisi TAM SIFIR",
        _ee295.qnt_katkisi_sifir_mi() is True)
kontrol("madde 295: majorler rastgele sembolden KAT KAT agir",
        _ee295.majorler_rastgeleden_agir_mi(5.0) is True)
kontrol("madde 295: FAZ cesitlendirmesi bacak buyuklugunden degerli",
        _ee295.faz_bacaktan_degerli_mi() is True)
kontrol("madde 295: basamak fonksiyonu olculen degerleri veriyor",
        abs(_ee295.evren_maliyeti(10.0) + 30.98) < 1e-9
        and abs(_ee295.evren_maliyeti(20.0) + 13.36) < 1e-9
        and abs(_ee295.evren_maliyeti(90.0)) < 1e-9)
kontrol("madde 295: standart 15x5 1.000 $'da CALISMAZ",
        _ee295.standart_1000de_calisir_mi() is False)
kontrol("madde 295: oneri (13x3) iki bakiyede de EN IYI uygun",
        _ee295.oneri_en_iyi_mi() is True)
kontrol("madde 295: standart 15x5 2.000 $'da 10+ puan geride",
        _ee295.standart_2000de_geride_mi(10.0) is True)
kontrol("madde 295: 1.000->2.000 atlamasi +17,6 puan ve UCURUMDAN",
        _ee295.atlama_degeri_dogru_mu() is True
        and _ee295.atlama_ucurumdan_mi() is True)
kontrol("madde 295: oneri botun env degiskenleriyle ifade edilebilir",
        "CARRY_N_DILIM" in _kaynak and "CARRY_N_LEGS" in _kaynak
        and "CARRY_MIN_LEGS" in _kaynak)
kontrol("madde 295: MIN_LEGS tutarsizligi NOT edildi",
        "tesadut" in _ee295.MIN_LEGS_NOTU or "tesaduf" in _ee295.MIN_LEGS_NOTU)
kontrol("madde 295: botun BAYAT docstring'i kayitli (SOL)",
        _ee295.docstring_bayat_mi() is True)
kontrol("madde 295: iki sapmam da KAYITLI",
        _ee295.iki_sapmam_kayitli_mi() is True)
kontrol("madde 295: ucurumun FIYATA bagliligi kayitli",
        "DOGRU ORANTILI" in _ee295.UCURUM_FIYATA_BAGLI)
kontrol("madde 295: varsayilanlar DEGISMEDI (15 dilim, 5 bacak)",
        cb.N_DILIM == 15 and cb.N_LEGS == 5)
kontrol("kâr haritası madde 295'i adresli-kayip yasası olarak yazdı",
        "Madde 295" in _harita and "ADRESLİ OLDUĞU YERDE" in _harita)

print("\n6ap) MADDE 296 - IKAME ENSTRUMAN")
import arastirma_ikame_enstruman as _ie296

kontrol("madde 296: odul ONCE olculdu ve buyuk (+28,5 puan)",
        _ie296.odul_buyuk_mu(20.0) is True
        and abs(_ie296.odul_puani() - 28.48) < 0.1)
kontrol("madde 296: en degerli iki ikame (BTC, ETH) CALISMIYOR",
        _ie296.en_degerli_ikameler_calisiyor_mu() is False)
kontrol("madde 296: ETHU funding korelasyonu ~0 (dayanak degil SINYAL)",
        _ie296.FUNDING[("ETHUSDT", "ETHU")][1] < 0.10)
kontrol("madde 296: ciddiye alinabilir ikameler yalniz BCHUSDC+AVAXUSDC",
        _ie296.ciddiye_alinabilir_ikameler() == ["AVAXUSDC", "BCHUSDC"])
kontrol("madde 296: BTCU/ETHU YENI LISTELENMIS olarak elendi",
        set(_ie296.yeni_listelenmisler()) == {"BTCU", "ETHU", "ETHUSD1"})
kontrol("madde 296: BTCU likiditesi 1000+ kat ince",
        _ie296.btcu_likiditesi_asiri_ince_mi(1000.0) is True)
kontrol("madde 296: iki ciddi ikame 10 $ bacakta +10,41 puan kurtarir",
        abs(_ie296.iki_ikame_ne_kurtarir() - 10.41) < 0.05)
kontrol("madde 296: ayni kurtarmanin 2.000 $'da degeri SIFIR",
        _ie296.ikibin_dolarda_degeri_sifir_mi() is True)
kontrol("madde 296: ince quote ciftleri HEPSI daha cok carry oduyor",
        _ie296.ince_ciftler_daha_cok_mu_oduyor() is True
        and _ie296.ortalama_fazla() > 1.0)
kontrol("madde 296: ACIK EKSEN olarak kayitli (yeni evren, olculmedi)",
        _ie296.acik_eksen_kayitli_mi() is True)
kontrol("madde 296: iki yasa da kayitli",
        "SINYALI icin alirsin" in _ie296.YASA1
        and "KIRILGAN" in _ie296.YASA2)
kontrol("madde 296: ayar DEGISMEDI",
        _ie296.ayar_degisti_mi() is False)
kontrol("kâr haritası madde 296'yi enstruman-sinyal yasası olarak yazdı",
        "Madde 296" in _harita and "SİNYALİ İÇİN ALIRSIN" in _harita)

print("\n6aq) MADDE 297 - HACIM ESIGI / BASKA COINLER")
import arastirma_evren_hacim as _eh297

_cd297_src = open(os.path.join(R, "carry_denetim.py"), encoding="utf-8").read()
_readme297 = open(os.path.join(R, "README.md"), encoding="utf-8").read()
_nerede297 = open(os.path.join(R, "NEREDE_NE_VAR.md"), encoding="utf-8").read()

kontrol("madde 297: USUSDT evrende VAR ama hacimden eleniyor (21/1576)",
        _eh297.USUSDT["uygun_bar"] == 21
        and _eh297.USUSDT["fiyat_gozlem"] == 1576
        and _eh297.USUSDT["medyan_hacim"] < _eh297.ESIK_SIMDI)
kontrol("madde 297: USUSDT funding BTC'nin 4+ kati (sinyal onu ISTIYOR)",
        _eh297.USUSDT["funding_yillik"]
        > 4.0 * _eh297.BTC_FUNDING_YILLIK)
kontrol("madde 297: esik 1e8 IKI YONDE de en iyi (ic optimum)",
        _eh297.esik_ic_optimum_mu() is True)
kontrol("madde 297: net doz-tepkisi iki yonde TEK YONLU dusuyor",
        _eh297.tek_yonlu_dusus_mu() is True)
kontrol("madde 297: dokuz kolun HICBIRI kanit esigini (%80) gecmedi",
        _eh297.gecen_aday_var_mi() is False)
kontrol("madde 297: en yakin rakip 7,5e7 ve o da sart 1'den dustu",
        abs(_eh297.EN_YAKIN_RAKIP - 7.5e7) < 1.0
        and _eh297.INCE_TARAMA[7.5e7][6] < _eh297.BAR_P
        and _eh297.INCE_TARAMA[7.5e7][1] < _eh297.KONTROL["sh22"])
kontrol("madde 297: TRADFI karisimi referans kolla elendi (fark 0)",
        _eh297.karisim_elendi_mi() is True
        and _eh297.REFERANS_KOL == "HACIM_ESIK=99999999")
kontrol("madde 297: esik 2e7'de bacaklarin %40'i ince coine kayiyor",
        _eh297.ince_coin_slot_payi() > 40.0)
kontrol("madde 297: bir slotun firsat maliyeti 17,66 bp/bacak",
        abs(_eh297.firsat_maliyeti_bp() - 17.66) < 0.05)
kontrol("madde 297: ince coinin FIYAT bacagi her katmanda negatif",
        _eh297.ince_coin_fiyat_bacagi_negatif_mi() is True)
kontrol("madde 297: ince coin funding'in YARISINI topluyor",
        _eh297.KATMAN_2E7["2e7-5e7"][3]
        < 0.6 * _eh297.KATMAN_2E7[">1e8"][3])
kontrol("madde 297: faz asimetrisi (Sh22 iyilesir, Sh25 coker) KAYITLI",
        _eh297.faz_asimetrisi_var_mi() is True)
kontrol("madde 297: USUSDT'de kitap da SHORT'tu (yon cakismasi)",
        _eh297.ususdt_sinyali_kullaniciyla_ayni_mi() is True)
kontrol("madde 297: ...ve yine de bacak basina 105 bp KAYBETTI",
        _eh297.ususdt_kitapta_kaybetti_mi() is True
        and abs(_eh297.USUSDT_BACAK["pnl_bp"] + 105.05) < 0.01)
kontrol("madde 297: fiyatta odenen, carry'nin 30+ kati",
        _eh297.ususdt_carry_fiyati_karsilamiyor_mu()[1] > 30.0)
kontrol("madde 297: USUSDT funding hic negatife donmedi",
        min(_eh297.USUSDT_FUNDING_AYLIK.values()) > 0)
kontrol("madde 297: spread hacim dustukce artiyor (2,31 -> 7,36 bp)",
        _eh297.spread_hacimle_artiyor_mu() is True)
kontrol("madde 297: en ince katmanin spread'i ALT TAHMIN olarak isaretli",
        _eh297.SPREAD_ALT_TAHMIN == "3e6-1e7"
        and "kirpar" in _eh297.SPREAD_SAPMA)
kontrol("madde 297: red OLCULMEMIS maliyet eksenine DAYANMIYOR",
        _eh297.maliyet_karara_girdi_mi() is False
        and "maker" in _eh297.MALIYET_KARARA_GIRMEDI)
kontrol("madde 297: motor kom'u canli maker ucretiyle ayni",
        abs(_eh297.MOTOR_KOM - 0.0002) < 1e-9)
kontrol("madde 297: SINYAL paneli GUNLUK oran (kaynak duzeltildi)",
        _eh297.SINYAL_BIRIMI == "gunluk"
        and "GÜNLÜK oran (MADDE 297" in _cd297_src
        and "# SİNYAL: yıllıklaştırılmış oran" not in _cd297_src)
kontrol("madde 297: ayar DEGISMEDI (CARRY_MIN_VOLUME=1e8)",
        _eh297.ayar_degisti_mi() is False
        and _eh297.AYAR["CARRY_MIN_VOLUME"] == int(cb.MIN_DAILY_VOLUME_USD))
kontrol("madde 297: hukum RED ve gerekcesi mekanizma",
        _eh297.hukum().startswith("RED")
        and "105 bp" in _eh297.hukum())
kontrol("madde 297: uc yasa da yazili",
        "SLOT" in _eh297.YASA1 and "RISKIN" in _eh297.YASA2
        and "DOGRULAMA DEGIL" in _eh297.YASA3)
kontrol("madde 297: TREND ekseni ACIK EKSEN olarak kayitli",
        _eh297.acik_eksen_kayitli_mi() is True)
kontrol("kâr haritası madde 297'yi slot-dagitimi yasasi olarak yazdi",
        "Madde 297" in _harita and "SLOT DAĞITIR" in _harita)
kontrol("README madde 297'yi tasiyor",
        "## 297." in _readme297 and "+200,85" in _readme297)
# MADDE 298: baslik sayaci her turda artiyor, o yuzden bu test maddenin
# KENDI SATIRINI arar - sayaci degil (sayaci en son madde test eder).
kontrol("NEREDE_NE_VAR madde 297'nin satirini tasiyor",
        "| **297** |" in _nerede297)

print("\n6ar) MADDE 298 - TREND KITABI / PLASEBO ESIGI")
import arastirma_trend_kitabi as _tk298
import arastirma_kural_gucu as _kg298

kontrol("madde 298: kullanici KAYBEDENI shortladi (momentum kolu)",
        _tk298.kullanici_momentum_kolunda_mi() is True
        and all(v < 0 for v in _tk298.USUSDT_GIRIS_GETIRI.values()))
kontrol("madde 298: bt2'nin min_bacak varsayilani hatasi KAYITLI",
        "min_bacak=8" in _tk298.BT2_HATA and "SIFIR" in _tk298.BT2_HATA)
kontrol("madde 298: carry AYNI ham motorda referans olarak olculdu",
        abs(_tk298.BT2_REFERANS_SHARPE - 0.648) < 0.01)
kontrol("madde 298: ham motorun maliyeti g33'un UC KATI",
        abs(_tk298.BT2_KOM / 0.0002 - 3.0) < 1e-9)
kontrol("madde 298: ham taramada isaret HER bakista tek yonlu",
        _tk298.bt2_isaret_tek_yonlu_mu() is True
        and _tk298.bt2_en_iyi_gun() == 1)
kontrol("madde 298: mom1 sartnameyi (2,5) gecti",
        _tk298.sartname_gecti_mi() is True)
kontrol("madde 298: AMA sartname esigi plasebonun BIR PUAN ustunde DEGIL",
        _tk298.sartname_yeterince_yukarida_mi() is False
        and _tk298.sartname_payi() > 75.0)
kontrol("madde 298: makine HIC SINYAL YOKKEN Sharpe ~2,0 veriyor",
        abs(_tk298.PLASEBO_SHARPE - 1.999) < 0.01)
kontrol("madde 298: carry'nin sinyali momentumun sinyalinden DEGERLI",
        _tk298.SINYAL_DEGERI["carry"] > _tk298.SINYAL_DEGERI["momentum"])
kontrol("madde 298: mom1 plaseboyu %95 barinin uzerinde gecti",
        _tk298.plaseboyu_gecti_mi() is True
        and _tk298.MOM_VS_PLASEBO["P_sharpe"] >= 95.0)
kontrol("madde 289'un SARTNAMESI madde 298'de plaseboyla duzeltildi",
        "plasebo_sharpe" in _kg298.SARTNAME
        and _kg298.SARTNAME["plaseboyu_gecme_P_min"] == 95.0
        and "MADDE 298" in _kg298.SARTNAME_MADDE298_NOTU)
kontrol("madde 289'un 'boyle kitap BULUNMADI' notu duzeltildi",
        "MADDE 298 DUZELTMESI" in _kg298.SIMULASYON_UYARISI
        and "ARTIK BULUNDU" in _kg298.SIMULASYON_UYARISI)
kontrol("madde 298: hasatli muhasebe YAPAYDI (hasatsizda fiyat pozitif)",
        _tk298.muhasebe_yapay_mi() is True)
kontrol("madde 298: hasat kapanmasi CIKTIDAN dogrulandi",
        "CIKTIDAN dogrulandi" in _tk298.HASAT_KAPATMA
        and _tk298.HASATSIZ_MUHASEBE["LONG tp"] == 0.0)
kontrol("madde 298: hasat-kapali kurulum madde 290 ile birebir",
        abs(_tk298.MADDE290_PARITE["carry hasatsiz sharpe"] - 2.33) < 0.01)
kontrol("madde 298: momentum makineye carry'den DAHA BAGIMLI",
        _tk298.momentum_makineye_daha_mi_bagimli() is True)
kontrol("madde 298: harman w=0,2'de kanit barini (P(Sh)>=%80) gecti",
        _tk298.harman_kanit_barini_gecti_mi(0.2) is True)
kontrol("madde 298: ham getiri niceligi aday DUSURUYOR (olcu uyusmazligi)",
        _tk298.HAM_GETIRI_P < 50.0 and "RISKTE" in _tk298.OLCU_UYUSMAZLIGI)
kontrol("madde 298: harman YALNIZ sart 4'ten dustu",
        _tk298.yalniz_sart4ten_mi_dustu() is True
        and _tk298.HARMAN_KALDIRAC[0.2] > 1.005)
kontrol("madde 298: sart 4'ten tek basina dusen UCUNCU aday",
        _tk298.SART4_DUSEN_ADAY_SAYISI == 3)
kontrol("madde 298: dusus azaltmasi sleeve'e AIT DEGIL (plasebo >= mom1)",
        _tk298.dusus_azaltmasi_sleeve_e_mi_ait() is False
        and _tk298.SLEEVE_DEGISTI["PLASEBO"][3]
        >= _tk298.SLEEVE_DEGISTI["mom1"][3])
kontrol("madde 298: ters-sinyal sleeve'i EN YUKSEK dozu verdi",
        _tk298.SLEEVE_DEGISTI["ters7"][3]
        == max(v[3] for v in _tk298.SLEEVE_DEGISTI.values()))
kontrol("madde 298: yalniz 1 gunluk bakis calisiyor (mom7/mom30 duser)",
        _tk298.yalniz_bir_geriye_bakis_mi_calisiyor() is True)
kontrol("madde 298: SECIM riski kayitli (7 bakis x 2 isaret tarandi)",
        _tk298.TARANAN_KOMBINASYON == 14)
kontrol("madde 298: mom1 harmani PLASEBO harmanini %99+ gecti",
        _tk298.momentum_plasebo_sleeve_i_gecti_mi() is True
        and _tk298.HARMAN_VS_PLASEBO["P_sharpe"] >= 99.0)
kontrol("madde 298: +7,61 ayrismasi toplamı tutuyor",
        abs(_tk298.AYRISMA["genel cesitlendirme"]
            + _tk298.AYRISMA["momentumun sinyali"]
            - _tk298.AYRISMA["toplam (kontrole karsi)"]) < 0.01)
kontrol("madde 298: UCELE tahminim YANLIS cikti ve kayda gecti",
        _tk298.ucele_tahmini_dogru_muydu() is False
        and "YANLIS" in _tk298.TAHMIN_YANLIS)
kontrol("madde 298: sermaye esigi carry_bot'un KENDI formuluyle tutuyor",
        abs(_tk298.TABAN_PAYI - cb.taban_pay()) < 1e-9
        and abs(_tk298.ASGARI_BACAK
                - cb.MIN_NOTIONAL_USD * cb.ASGARI_BACAK_CARPANI) < 1e-9
        and abs(_tk298.SERMAYE_ESIGI["13x3"][0]
                - _tk298.ASGARI_BACAK * 13 * 3 / _tk298.TABAN_PAYI) < 1.0)
kontrol("madde 298: harman kullanici bakiyesinde KOSAMAZ",
        _tk298.kullanici_bakiyesinde_kosar_mi() is False
        and _tk298.gereken_sermaye() > max(_tk298.KULLANICI_BAKIYE))
kontrol("madde 298: ayar DEGISMEDI",
        _tk298.ayar_degisti_mi() is False)
kontrol("madde 298: hukum ACIK AMA UYGULANAMAZ",
        _tk298.hukum().startswith("ACIK AMA UYGULANAMAZ"))
kontrol("madde 298: dort yasa da yazili",
        "plasebo Sharpe'ini" in _tk298.YASA1
        and "SLEEVE'E ait olmayabilir" in _tk298.YASA2
        and "Nicelik secimi" in _tk298.YASA3
        and "sermaye bolunur" in _tk298.YASA4)
kontrol("kâr haritası madde 298'i plasebo-esigi yasasi olarak yazdi",
        "Madde 298" in _harita and "PLASEBO SHARPE'INI" in _harita)
kontrol("README madde 298'i tasiyor",
        "## 298." in _readme297 and "+208,46" in _readme297)
# MADDE 299: baslik sayaci her turda artiyor; bu test yalniz maddenin
# KENDI SATIRINI arar. Sayac TEK BIR yerde, tabloda en yuksek madde
# numarasindan TURETILEREK denetlenir (asagidaki 6as blogu).
kontrol("NEREDE_NE_VAR madde 298'in satirini tasiyor",
        "| **298** |" in _nerede297)

print("\n6as) MADDE 299 - SINYAL HARMANI / SK_DOSYA BUYUKLUK SEMANTIGI")
import arastirma_sinyal_harmani as _sh299
_g33src = open(os.path.join(R, "g33.py"), encoding="utf-8").read()

kontrol("madde 299: g33'e SK_DOSYA buyukluk uyarisi yazildi",
        "MADDE 299 UYARISI" in _g33src
        and "SADECE BIR SIRALAMA DEGIL" in _g33src)
kontrol("madde 299: uyari REZ_ESIK'i ve REZERV=0 tavsiyesini adiyla aniyor",
        "REZ_ESIK" in _g33src and "REZERV=0 ile KOS" in _g33src)
kontrol("madde 299: motorda REZ_ESIK gercekten S ile kiyaslaniyor",
        "S[i,k]<=-REZ_ESIK" in _g33src.replace(" ", "")
        and "S[i+1,k]<=-REZ_ESIK" in _g33src.replace(" ", ""))
kontrol("madde 299: parite kirilmasi SECIMDEN degildi (301 barda 0 fark)",
        _sh299.parite_kirilmasi_secimden_miydi() is False
        and _sh299.TANI_BAR_SAYISI == 301 and _sh299.TANI_FARKLI_BAR == 0)
kontrol("madde 299: yorum eklendikten sonra parite GERI GELDI",
        _sh299.parite_geri_geldi_mi() is True
        and _sh299.PARITE_YENIDEN == 0.0)
kontrol("madde 299: madde 298'in rezerv karisimi GERCEKTI (>=2 kat)",
        _sh299.rezerv_karisimi_var_miydi() is True
        and _sh299.REZERV_KULLANIMI["kontrol (funding)"] == 58
        and _sh299.REZERV_KULLANIMI["mom1"] == 214)
kontrol("madde 299: REZERV=0 ile madde 298'in hukmu AYAKTA",
        _sh299.madde298_hukmu_ayakta_mi() is True)
kontrol("madde 299: karisimin yonu adayin ALEYHINEYDI",
        _sh299.karisim_adayin_lehine_miydi() is False)
kontrol("madde 299: doz kazanci REZERV=0'da da sinyale AIT DEGIL",
        _sh299.doz_kazanci_sinyale_mi_ait() is False)
kontrol("madde 299: harman FUNDING biriminde ve w=0 bit duzeyinde ayni",
        _sh299.PARITE_BIT_AYNI is True
        and "sigma_F" in _sh299.HARMAN_FORMULU)
kontrol("madde 299: tam destek notu (satir 490) kayitli",
        "490" in _sh299.TAM_DESTEK_NOTU and "TUTULAN" in _sh299.TAM_DESTEK_NOTU)
kontrol("madde 299: hicbir agirlik kanit esigini gecmedi",
        _sh299.gecen_agirlik_var_mi() is False)
kontrol("madde 299: hepsi SART 1'den dustu",
        _sh299.hepsi_sart1den_mi_dustu() is True)
kontrol("madde 299: momentum icerigi GERCEK (plasebo harmanini geciyor)",
        _sh299.momentum_icerigi_gercek_mi() is True)
kontrol("madde 299: ama bedel katkidan BUYUK",
        _sh299.bedel_katkidan_buyuk_mu() is True
        and abs(_sh299.AYRISMA["egmenin mekanik bedeli"] + 34.02) < 0.01
        and abs(_sh299.AYRISMA["momentumun icerigi"] - 12.13) < 0.01)
kontrol("madde 299: ayrisma toplami TUTUYOR (netlerden turetildi)",
        abs(_sh299.AYRISMA["egmenin mekanik bedeli"]
            + _sh299.AYRISMA["momentumun icerigi"]
            - _sh299.AYRISMA["kalan (kontrole karsi)"]) < 0.01)
kontrol("madde 299: PLATO var (22-24 kaybi doza duyarsiz)",
        _sh299.plato_var_mi() is True)
kontrol("madde 299: momentumun kenari SON REJIMDE",
        _sh299.son_rejime_mi_ait() is True)
kontrol("madde 299: sinyal harmani sermaye bolmezdi (975 < 4875)",
        _sh299.sinyal_harmani_sermaye_bolmuyor_mu() is True)
kontrol("madde 299: kullanici icin degisen YOK, oneri ayni",
        _sh299.kullanici_icin_degisen_var_mi() is False
        and "13 dilim x 3 bacak" in _sh299.ONERI)
kontrol("madde 299: ayar DEGISMEDI",
        _sh299.ayar_degisti_mi() is False)
kontrol("madde 299: hukum RED",
        _sh299.hukum().startswith("RED"))
kontrol("madde 299: bes yasa da yazili",
        "SERMAYEDE" in _sh299.YASA1 and "SIRALAMA" in _sh299.YASA2
        and "VARSAYILMAZ" in _sh299.YASA3 and "YONU" in _sh299.YASA4
        and "PLATO" in _sh299.YASA5)
kontrol("madde 298 dosyasi madde 299'un duzeltmesini TASIYOR",
        hasattr(_tk298, "MADDE299_KARISIMI")
        and _tk298.madde299_karisimi_hukmu_degistirdi_mi() is False)
kontrol("kâr haritası madde 299'u sermaye-vs-sinyal yasasi olarak yazdi",
        "Madde 299" in _harita and "SERMAYEDE YAPMAK" in _harita)
kontrol("README madde 299'u tasiyor",
        "## 299." in _readme297 and "+178,96" in _readme297)
kontrol("NEREDE_NE_VAR madde 299'un satirini tasiyor",
        "| **299** |" in _nerede297)
# MADDE 299: sayac artik ELLE yazilmiyor - tabloda en yuksek madde
# numarasindan turetiliyor, boylece her yeni turda kirilmaz.
_madde_no = [int(m) for m in re.findall(r"\| \*\*(\d{2,4})\*\* \|", _nerede297)]
kontrol("NEREDE_NE_VAR basliktaki sayac EN YUKSEK madde ile tutuyor",
        bool(_madde_no)
        and f"{max(_madde_no)} numaralı madde var" in _nerede297)

print("\n6at) MADDE 300 - TP ESIKLERI 13x3 KITABINDA")
import arastirma_tp_kucuk_kitap as _tp300
import arastirma_evren_esigi as _ee300

kontrol("madde 300: 13x3 kontrolu madde 295'in DUSUS kaydiyla BIREBIR",
        _tp300.kontrol_madde295_ile_tutuyor_mu() is True
        and abs(_tp300.KONTROL["dd"] - _ee300.DUSUS["13x3"]) < 0.01)
kontrol("madde 300: net farki madde 295'in YAPISAL kaydiyla BIREBIR",
        _tp300.yapisal_maliyet_tutuyor_mu() is True
        and abs((_tp300.KONTROL["net"] - _tp300.KONTROL_15X5["net"])
                - _ee300.YAPISAL["13x3"]) < 0.05)
kontrol("madde 300: alti kolun HICBIRI kanit barini gecmedi",
        _tp300.gecen_kol_var_mi() is False and len(_tp300.TARAMA) == 6)
kontrol("madde 300: en yakin kol TPS 0,28 ve o da gurultu",
        _tp300.en_yakin_kol() == "TPS 0,28"
        and _tp300.TARAMA["TPS 0,28"][7] < 50.0)
kontrol("madde 300: ham getiri olcusu TPL 0,55'i KABUL ederdi",
        _tp300.ham_olcu_yanlis_kabul_eder_mi() is True
        and _tp300.AYNA["ham getiri P"] >= 95.0)
kontrol("madde 300: ...ama doz olcusu REDDEDIYOR",
        _tp300.AYNA["doz net farki"] < 0
        and _tp300.TARAMA["TPL 0,55"][5] < _tp300.KONTROL["doz"])
kontrol("madde 300: nicelik hatasi IKI YONLU oldugu kayitli",
        _tp300.nicelik_hatasi_iki_yonlu_mu() is True)
kontrol("madde 300: TPL'nin ALT kenari sert (-51,47 puan)",
        _tp300.tpl_alt_kenari_sert_mi() is True
        and abs(_tp300.TPL_ALT_UCURUM["net_farki"] + 51.47) < 0.01)
kontrol("madde 300: TPS 0,20 ustu PLATO",
        _tp300.tps_plato_mu() is True)
kontrol("madde 300: TPS 0,20 alti SERT",
        _tp300.tps_alt_kenari_sert_mi() is True)
kontrol("madde 300: esik sekli ASIMETRIK ve 13x3'te de ayakta",
        _tp300.esik_sekli_asimetrik_mi() is True
        and _tp300.ASIMETRI_13X3_DE_AYAKTA is True)
kontrol("madde 300: cozunurluk cekincesi KAYITLI",
        "TAM YERI olculmedi" in _tp300.COZUNURLUK_CEKINCESI)
kontrol("madde 300: ayar DEGISMEDI ve carry_bot ile tutuyor",
        _tp300.ayar_degisti_mi() is False
        and abs(_tp300.AYAR["TPL"] - 0.40) < 1e-9
        and abs(_tp300.AYAR["TPS"] - 0.20) < 1e-9)
kontrol("madde 300: hukum RED ve ters-yon bulgusunu aniyor",
        _tp300.hukum().startswith("RED") and "%95,9" in _tp300.hukum())
kontrol("madde 300: uc yasa da yazili",
        "IKI YONDE" in _tp300.YASA1 and "ayni sekle" in _tp300.YASA2
        and "MEKANIZMAYA" in _tp300.YASA3)
kontrol("madde 299'un yasa 3'u madde 300 ekiyle guncellendi",
        hasattr(_sh299, "YASA3_MADDE300_EKI")
        and "KABUL de eder" in _sh299.YASA3_MADDE300_EKI)
kontrol("madde 298'in olcu-uyusmazligi sabiti madde 300'u aniyor",
        "MADDE 300" in _tk298.OLCU_UYUSMAZLIGI)
kontrol("kâr haritası madde 300'u nicelik yasasi olarak yazdi",
        "Madde 300" in _harita and "İKİ YÖNDE DE HATA YAPAR" in _harita)
kontrol("README madde 300'u tasiyor",
        "## 300." in _readme297 and "+195,33" in _readme297)
kontrol("NEREDE_NE_VAR madde 300'un satirini tasiyor",
        "| **300** |" in _nerede297)

print("\n6au) MADDE 301 - EMIR SIRASI BELIRLENIMLI")
import arastirma_emir_sirasi as _es301

# ASIL DAVRANIS TESTI: ayni girdi, defalarca, AYNI sira cikmali.
_h301 = {f"C{i}USDT": (100.0 if i % 2 == 0 else -100.0) for i in range(10)}
_s301 = [tuple(e[0] for e in cb.emirleri_hesapla(_h301, {}, 1.0))
         for _ in range(5)]
kontrol("madde 301: esit bacaklarda emir sirasi TEKRARLANABILIR",
        len(set(_s301)) == 1, f"({len(set(_s301))} ayri sira)")
kontrol("madde 301: sira ALFABETIK (beraberlik ikincil anahtarla kirilir)",
        list(_s301[0]) == sorted(_s301[0], key=lambda x: x))
# ASIL KORUMA: ayni surecte tekrarlamak hash rastgeleligini YAKALAMAZ
# (tohum surec basina sabit). Gerilemeyi yakalayacak tek test, AYRI
# SURECLERDE ayri PYTHONHASHSEED ile kosmaktir.
import subprocess as _sp301
_kod301 = (
    "import carry_bot as cb;"
    "h={('C%dUSDT'%i):(100.0 if i%2==0 else -100.0) for i in range(10)};"
    "print(','.join(e[0] for e in cb.emirleri_hesapla(h,{},1.0)))")
_alt301 = set()
for _t301 in ("0", "7", "42", "12345"):
    _env301 = dict(os.environ, PYTHONHASHSEED=_t301)
    _r301 = _sp301.run([sys.executable, "-c", _kod301], cwd=R,
                       capture_output=True, text=True, env=_env301, timeout=120)
    if _r301.returncode == 0:
        _alt301.add(_r301.stdout.strip())
kontrol("madde 301: AYRI SURECLERDE (4 hash tohumu) sira AYNI",
        len(_alt301) == 1, f"({len(_alt301)} ayri sira)")
kontrol("madde 301: madde 208'in DOKUMASI korundu (taraflar alternatifli)",
        all((i % 2 == 0) == (_h301[s_] > 0) for i, s_ in enumerate(_s301[0])))
_n301 = [sum(1 if _h301[s_] > 0 else -1 for s_ in _s301[0][:k])
         for k in range(1, len(_s301[0]) + 1)]
kontrol("madde 301: her kesme noktasinda |net| en fazla BIR bacak",
        max(abs(x) for x in _n301) <= 1, f"({_n301})")
kontrol("madde 301: buyukluk sirasi hala BIRINCIL (buyuk once)",
        [e[2] for e in cb.emirleri_hesapla(
            {"AUSDT": 50.0, "BUSDT": 200.0}, {}, 1.0)] == [200.0, 50.0])
kontrol("madde 301: kaynakta ikincil anahtar YAZILI",
        "MADDE 301" in _kaynak and "(-e[2], e[0])" in _kaynak)
kontrol("madde 301: kararsizlik KAYITLI ve tekrar kosuda gecmisti",
        _es301.test_kararsiz_miydi() is True
        and len(_es301.DUSEN_TESTLER) == 3)
kontrol("madde 301: hash olcumu bes tohumda bes AYRI sira buldu",
        _es301.hash_sirasi_rastgele_miydi() is True)
kontrol("madde 301: duzeltme belirlenimli (6 tohum, 1 sira)",
        _es301.duzeltme_belirlenimli_mi() is True)
kontrol("madde 301: buyukluk sirasi korundu olarak kayitli",
        _es301.buyukluk_sirasi_korundu_mu() is True)
kontrol("madde 301: notrluk bozulmamisti (madde 208 ayakta)",
        _es301.notrluk_bozulmus_muydu() is False)
kontrol("madde 301: geri test ETKILENMEDI",
        _es301.geri_test_etkilendi_mi() is False)
kontrol("madde 301: temiz_ortam sizintisi kayitli ve su an zararsiz",
        set(_es301.TEMIZ_ORTAM_EKSIK)
        == {"TP_DEFTER_DOSYA", "TP_KURULUM_DOSYA"}
        and _es301.sizinti_su_an_zararli_mi() is False)
kontrol("madde 301: o iki defter gercekten bir_tur icinde OKUNMUYOR",
        "tp_dolum_oku(" not in _kaynak.split("def bir_tur")[-1]
        and "tp_kurulum_oku(" not in _kaynak.split("def bir_tur")[-1])
kontrol("madde 301: ayar DEGISMEDI",
        _es301.ayar_degisti_mi() is False)
kontrol("madde 301: dort yasa da yazili",
        "ORTBAS" in _es301.YASA1 and "SAKLAR" in _es301.YASA2
        and "uretilebilirlik" in _es301.YASA3 and "yarin okunur" in _es301.YASA4)
kontrol("kâr haritası madde 301'i kararsiz-test yasasi olarak yazdi",
        "Madde 301" in _harita and "ÖRTBAS ETMEKTİR" in _harita)
kontrol("README madde 301'i tasiyor",
        "## 301." in _readme297 and "PYTHONHASHSEED" in _readme297)
kontrol("NEREDE_NE_VAR madde 301'in satirini tasiyor",
        "| **301** |" in _nerede297)

print("\n6av) MADDE 302 - DEVRE KESICI KALIBRASYONU")
import arastirma_devre_kesici_kalibrasyon as _dk302

# --- ASIL DAVRANIS: esikler yapilandirmadan TURETILIYOR mu? ---
kontrol("madde 302: 15x5'te olcek 1,000 - varsayilan BIREBIR AYNI",
        abs(cr.dusus_olcegi("15x5")[0] - 1.0) < 1e-9
        and abs(cr.dusus_incele("15x5") - cr.DUSUS_INCELE) < 1e-12
        and abs(cr.dusus_durdur("15x5") - cr.DUSUS_DURDUR) < 1e-12)
# MADDE 303 GUNCELLEMESI: bu kontrol madde 302'de -0,219/-0,280 (dusus
# oraniyla olcekleme) bekliyordu. Madde 303 madde 231'in KANONIK yontemini
# uygulayip -0,23/-0,29 olctu ve esik oraya cekildi. Kontrol artik
# "13x3 esigi 15x5'ten BELIRGIN gevsek ve kanonik olcumle ayni" diyor;
# tam deger 6aw blogunda denetleniyor.
kontrol("madde 302+303: 13x3 esigi 15x5'ten belirgin gevsek",
        abs(cr.dusus_incele("13x3")) > abs(cr.DUSUS_INCELE) * 1.2
        and abs(cr.dusus_durdur("13x3")) > abs(cr.DUSUS_DURDUR) * 1.2)
kontrol("madde 302: olcek 13x3'un OLCULMUS dususunden geliyor",
        abs(cr.dusus_olcegi("13x3")[0]
            - cr.KITAP_DUSUS["13x3"] / cr.KITAP_DUSUS["15x5"]) < 1e-12)
kontrol("madde 302: KITAP_DUSUS tablosu madde 295'in olcumuyle AYNI",
        all(abs(cr.KITAP_DUSUS[k] - _ee300.DUSUS[k]) < 0.01
            for k in _ee300.DUSUS if k in cr.KITAP_DUSUS)
        and len(cr.KITAP_DUSUS) == len(_ee300.DUSUS))
kontrol("madde 302: bilinmeyen yapilandirmada esik GEVSETILMIYOR + uyari",
        abs(cr.dusus_olcegi("7x7")[0] - 1.0) < 1e-9
        and "UYARI" in cr.dusus_olcegi("7x7")[1])
kontrol("madde 302: riskli yapilandirmalar daha GEVSEK esik aliyor",
        cr.dusus_incele("1x5") < cr.dusus_incele("13x3") < cr.dusus_incele("15x5"))
kontrol("madde 302: SABIT KODLU '-14.7' mesaji kaldirildi",
        "%-14.7" not in open(os.path.join(R, "carry_rapor.py"),
                             encoding="utf-8").read())
kontrol("madde 302: backtest_maksimumu yapilandirmaya gore donuyor",
        abs(cr.backtest_maksimumu("15x5") - 14.54) < 0.01
        and abs(cr.backtest_maksimumu("13x3") - 17.68) < 0.01)
kontrol("madde 302: kitap_anahtari carry_bot'un ayarini okuyor",
        cr.kitap_anahtari() == f"{cb.N_DILIM}x{cb.N_LEGS}")

# --- OLCUM KAYITLARI ---
kontrol("madde 302: 13x3'un INCELE payi 1 puandan AZDI",
        _dk302.pay_erimis_miydi() is True
        and _dk302.PAY_PUAN["13x3"] < 0.5)
kontrol("madde 302: yontem madde 243'un tablosuyla DOGRULANDI",
        _dk302.yontem_dogrulandi_mi() is True)
kontrol("madde 302: eski esik 13x3'te yilda %20+ yanlis tetikliydi",
        _dk302.eski_esik_13x3_te_yanlis_tetikli_mi() is True
        and _dk302.DD_DAGILIMI["13x3"][3] > 30.0)
kontrol("madde 302: DURDUR sanssizliktan tetiklenebiliyordu (bot KAPANIR)",
        _dk302.durdur_sanssizliktan_tetiklenir_mi() is True)
kontrol("madde 302: iki turetme AYNI yuvarlakta bulustu",
        _dk302.iki_turetme_bulustu_mu() is True
        and _dk302.turetmeler_ayni_yuvarlakta_mi() is True)
kontrol("madde 302: yeni esik 15x5'in kalibrasyonuyla ESDEGER",
        _dk302.yeni_esik_esdeger_mi() is True)
kontrol("madde 302: ilk ayda zarar NORMAL olarak kayitli (P ~%20)",
        _dk302.ilk_ay_zarar_normal_mi() is True
        and 15.0 < _dk302.CEYREK[30][0] < 25.0)
kontrol("madde 302: ilk ceyrek sorunu KUCUK (abartilmadi)",
        _dk302.ceyrek_sorunu_kucuk_mu() is True
        and _dk302.ILK_CEYREK_TETIK[90][0] < 5.0)
kontrol("madde 302: strateji ayari DEGISMEDI",
        _dk302.ayar_degisti_mi() is False)
kontrol("madde 302: dort yasa da yazili",
        "KITABA aittir" in _dk302.YASA1 and "URETEN kurali" in _dk302.YASA2
        and "YONTEMI eski sonucla" in _dk302.YASA3
        and "BUYUK gostermek" in _dk302.YASA4)
kontrol("kâr haritası madde 302'yi esik-kitap yasasi olarak yazdi",
        "Madde 302" in _harita and "TÜRETİLDİĞİ KİTABA AİTTİR" in _harita)
kontrol("README madde 302'yi tasiyor",
        "## 302." in _readme297 and "%30,6" in _readme297)
kontrol("NEREDE_NE_VAR madde 302'nin satirini tasiyor",
        "| **302** |" in _nerede297)

print("\n6aw) MADDE 303 - KANONIK REJIM ESIKLERI")
import arastirma_rejim_esik as _re303
import arastirma_rejim as _rj303

# --- ASIL DAVRANIS: uc kademe dogru mu? ---
kontrol("madde 303: 15x5 OLCULMUS kademede ve temel sabitlerle AYNI",
        cr.esik_kademesi("15x5") == "olculmus"
        and cr.dusus_incele("15x5") == cr.DUSUS_INCELE
        and cr.dusus_durdur("15x5") == cr.DUSUS_DURDUR)
kontrol("madde 303: 13x3 OLCULMUS kademede ve -%23 / -%29",
        cr.esik_kademesi("13x3") == "olculmus"
        and abs(cr.dusus_incele("13x3") + 0.23) < 1e-9
        and abs(cr.dusus_durdur("13x3") + 0.29) < 1e-9)
kontrol("madde 303: 13x3 esigi madde 302'ye gore GEVSEDI",
        abs(cr.dusus_incele("13x3")) > 0.219)
kontrol("madde 303: olculmemis ama dususu bilinen kitap OLCEKLENIYOR",
        cr.esik_kademesi("5x5") == "olceklenmis"
        and cr.dusus_incele("5x5") < cr.DUSUS_INCELE)
kontrol("madde 303: hic bilinmeyen kitap TEMEL'de kalir, GEVSETILMEZ",
        cr.esik_kademesi("7x7") == "temel"
        and cr.dusus_incele("7x7") == cr.DUSUS_INCELE)
kontrol("madde 303: KITAP_ESIK kanonik olcumle tutuyor",
        all(cr.KITAP_ESIK[k] == _re303.kanonik_esik(k) for k in cr.KITAP_ESIK))
kontrol("madde 303: rejim olcumu kaynakta kayitli (en kotu rejim + p5/p1)",
        set(cr.KITAP_REJIM_OLCUMU) == set(cr.KITAP_ESIK)
        and all(v[0] == "dusuk prim" for v in cr.KITAP_REJIM_OLCUMU.values()))
kontrol("madde 303: olculmus esik, rejim p1'inin BUYUKLUGUNU asmiyor",
        all(abs(cr.KITAP_ESIK[k][1]) >= abs(cr.KITAP_REJIM_OLCUMU[k][2]) / 100
            for k in cr.KITAP_ESIK))
kontrol("madde 303: rapor ozeti KADEMEYI de yaziyor",
        "esik_kademesi()" in open(os.path.join(R, "carry_rapor.py"),
                                  encoding="utf-8").read())

# --- OLCUM KAYITLARI ---
kontrol("madde 303: yontem madde 231'in UC rakamiyla dogrulandi",
        _re303.yontem_dogrulandi_mi() is True
        and len(_re303.DOGRULAMA_15X5) == 3)
kontrol("madde 303: madde 231'in REJIM kaydiyla ayni kirilma kullanildi",
        _re303.REJIM_KIRILMA == _rj303.REJIM_KIRILMA)
kontrol("madde 303: madde 233'un -%18'i en kotu rejim p5'iyle aciklandi",
        _re303.madde233_zinciri_tutuyor_mu() is True)
kontrol("madde 303: EN KOTU rejim iki kitapta da DUSUK PRIM",
        _re303.en_kotu_rejim_dogru_mu("15x5") is True
        and _re303.en_kotu_rejim_dogru_mu("13x3") is True)
kontrol("madde 303: madde 302 DOGRU YONDEYDI (%30,6 -> %12,6)",
        _re303.madde302_dogru_yonde_miydi() is True)
kontrol("madde 303: ...ama gereginden SIKIYDI (kisayol olcek EKSIK)",
        _re303.madde302_gereginden_siki_miydi() is True
        and _re303.kisayol_olcek_eksik_mi() is True)
kontrol("madde 303: kanonik esik 15x5'in kalibrasyonuyla ESDEGER",
        _re303.kanonik_esdeger_mi() is True)
kontrol("madde 303: madde 301'in fikstur sizintisi KAPATILDI",
        _re303.sizinti_kapandi_mi() is True
        and "cb.TP_DEFTER_DOSYA = os.path.join(d," in open(
            os.path.join(R, "test_carry_entegrasyon.py"),
            encoding="utf-8").read())
kontrol("madde 303: strateji ayari DEGISMEDI",
        _re303.ayar_degisti_mi() is False)
kontrol("madde 303: uc yasa da yazili",
        "yeni bir eksen acmadan ONCE kapat" in _re303.YASA1
        and "BUYUKLUKTE sapar" in _re303.YASA2
        and "OLCULDUGU mu TAHMIN" in _re303.YASA3)
kontrol("kâr haritası madde 303'u eksen-kapatma yasasi olarak yazdi",
        "Madde 303" in _harita and "YENİ BİR EKSEN AÇMADAN ÖNCE KAPAT" in _harita)
kontrol("README madde 303'u tasiyor",
        "## 303." in _readme297 and "−%22,66" in _readme297)
kontrol("NEREDE_NE_VAR madde 303'un satirini tasiyor",
        "| **303** |" in _nerede297)
kontrol("madde 302'nin belgeleri madde 303'e ILERI ISARET veriyor",
        hasattr(_dk302, "MADDE303_YURURLUKTEKI")
        and _dk302.madde303_bu_esigi_gevsetti_mi() is True
        and "MADDE 303 GÜNCELLEMESİ" in _readme297
        and "MADDE 303'te kanonik yöntemle" in _nerede297)
kontrol("madde 303: yururlukteki esik madde 302'nin degeri DEGIL",
        cr.dusus_incele("13x3") == _dk302.MADDE303_YURURLUKTEKI["incele"]
        and cr.dusus_incele("13x3") != _dk302.ESIK_YENI_13X3["incele"])

print("\n6ax) MADDE 304 - HAVUZ/REB VE SERMAYE MERDIVENI")
import arastirma_sermaye_merdiveni as _sm304

kontrol("madde 304: alti kolun HICBIRI kanit barini gecmedi",
        _sm304.gecen_kol_var_mi() is False and len(_sm304.TARAMA) == 6)
kontrol("madde 304: en yakin kol HAVUZ 5 ve o da gurultu",
        _sm304.en_yakin_kol() == "HAVUZ 5"
        and _sm304.TARAMA["HAVUZ 5"][7] < 50.0)
kontrol("madde 304: HAVUZ=3 ve REB=5 zaten en iyi",
        _sm304.havuz_reb_zaten_en_iyi_mi() is True)
kontrol("madde 304: uc eksen (TP/HAVUZ/REB) ayni cevabi verdi",
        _sm304.uc_eksen_ayni_cevabi_mi_verdi() is True)
kontrol("madde 304: ayna tuzagi artik bir DESEN (3 ornek)",
        _sm304.ayna_deseni_mi() is True and set(_sm304.AYNA_SICIL) == {299, 300, 304})
kontrol("madde 304: REB=3'un dozu 1,0'IN ALTINDA (ilk vaka)",
        _sm304.doz_birin_altina_dustu_mu() is True
        and _sm304.TARAMA["REB 3 gun"][5] < 1.0)
kontrol("madde 304: ham olcu REB=3'u KABUL ederdi (P>=%95, net DUSUK)",
        _sm304.ham_olcu_kabul_ederdi_mi() is True
        and _sm304.TARAMA["REB 3 gun"][8] >= 99.0)
kontrol("madde 304: merdivenin neti monoton ARTIYOR",
        _sm304.merdiven_neti_artiyor_mu() is True)
kontrol("madde 304: yapi sirasi MONOTON DEGIL (5x5 araya giriyor)",
        _sm304.merdiven_monoton_mu() is False)
kontrol("madde 304: merdiven projenin KENDI fonksiyonlariyla tutuyor",
        all(abs((_sm304.TABAN_NET + _ee300.toplam_maliyet(b, y)) - n) < 0.01
            for b, y, _l, n in _sm304.MERDIVEN))
kontrol("madde 304: merdivendeki her rung o bakiyede gercekten EN IYI",
        all(_ee300.en_iyi(b) == y for b, y, _l, _n in _sm304.MERDIVEN))
kontrol("madde 304: merdivendeki her yapi o bakiyede KOSABILIR",
        all(_ee300.uygun_mu(b, y) for b, y, _l, _n in _sm304.MERDIVEN))
kontrol("madde 304: bacak hesabi carry_bot'un formuluyle ayni",
        all(abs(_l - b * cb.taban_pay() / (_ee300.IZGARA[y][0]
                                           * _ee300.IZGARA[y][1])) < 0.01
            for b, y, _l, _n in _sm304.MERDIVEN))
kontrol("madde 304: kullanicinin 2.000 $ bacagi, rung bacagindan FARKLI",
        abs(_sm304.KULLANICI_BACAK
            - _sm304.KULLANICI_BAKIYE * cb.taban_pay() / 39) < 0.01
        and abs(_sm304.KULLANICI_BACAK - _sm304.simdiki_rung()[2]) > 0.4)
kontrol("madde 304: kullanici 13x3 rungunda ve sonraki adim 3.750 $",
        _sm304.simdiki_rung()[1] == "13x3"
        and abs(_sm304.sonraki_rung()[0] - 3750.0) < 1.0
        and abs(_sm304.sonraki_kazanc() - 5.52) < 0.01)
kontrol("madde 304: taban madde 295 ile CAPRAZ dogrulandi",
        _sm304.capraz_dogrulama_tutuyor_mu() is True)
kontrol("madde 304: sekiz eksen denendi, gecen YOK",
        _sm304.DENENEN_EKSEN_SAYISI == 8
        and _sm304.gecen_kol_var_mi() is False)
kontrol("madde 304: kendi hatam (kosabilirlik filtresi) KAYITLI",
        "KOSABILIRLIK" in _sm304.HATAM
        and "KENDINE" in _sm304.HATANIN_DERSI)
kontrol("madde 304: ayar DEGISMEDI",
        _sm304.ayar_degisti_mi() is False
        and "13 dilim x 3 bacak" in _sm304.ONERI)
kontrol("madde 304: dort yasa da yazili",
        "MEKANIZMAYA" in _sm304.YASA1 and "SISTEMATIK" in _sm304.YASA2
        and "SERMAYEDEDIR" in _sm304.YASA3
        and "yeniden turetme" in _sm304.YASA4)
kontrol("kâr haritası madde 304'u sermaye-merdiveni yasasi olarak yazdi",
        "Madde 304" in _harita and "KÂR PARAMETREDE DEĞİL SERMAYEDEDİR" in _harita)
kontrol("README madde 304'u tasiyor",
        "## 304." in _readme297 and "+181,97" in _readme297)
kontrol("NEREDE_NE_VAR madde 304'un satirini tasiyor",
        "| **304** |" in _nerede297)

print("\n6ay) MADDE 305 - TREND SLEEVE 13x3")
import arastirma_trend_13x3 as _t305

kontrol("madde 305: sinyalin degeri 13x3'te 15x5'ten BUYUK",
        _t305.sinyal_13x3_te_daha_mi_degerli() is True
        and _t305.SINYAL_DEGERI["13x3"] > 0.7)
kontrol("madde 305: tam evrende kazanc 15x5'in UC KATI",
        _t305.tam_evren_ucu_kat_mi() is True
        and _t305.HARMAN_TAM[0.3][7] > 20.0)
kontrol("madde 305: sart 1 iki fazda da TEMIZ (15x5'te kil payiydi)",
        _t305.sart1_temiz_mi() is True)
kontrol("madde 305: PLASEBO harmani her agirlikta NEGATIF",
        _t305.plasebo_harmani_negatif_mi() is True)
kontrol("madde 305: momentum plaseboyu hem tek basina hem harmanda gecti",
        _t305.momentum_plaseboyu_gecti_mi() is True
        and _t305.MOM_VS_PLASEBO_P >= 99.0)
kontrol("madde 305: tam evren GERCEKTEN fazla gosteriyordu",
        _t305.tam_evren_gercekten_fazla_mi() is True)
kontrol("madde 305: esik 9.375 $'dan 3.250 $'a DUSTU",
        _t305.esik_dustu_mu() is True
        and abs(_t305.ESIK_USD - 3250.0) < 1.0)
kontrol("madde 305: esik kullanici bakiyesinin ~1,6 kati",
        1.5 < _t305.esik_kati() < 1.8)
kontrol("madde 305: 2.000 $'da harman KOSMUYOR",
        _t305.kullanici_bakiyesinde_kosar_mi() is False
        and _t305.MERDIVEN[0][3] is None)
kontrol("madde 305: sleeve bacagi 2.000 $'da asgarinin ALTINDA",
        _t305.MERDIVEN[0][5] < _t305.ASGARI_BACAK)
kontrol("madde 305: her bakiyede sart 1-2-3 GECIYOR",
        _t305.her_bakiyede_sart123_geciyor_mu() is True)
kontrol("madde 305: her bakiyede kanit bari (>=%80) GECILIYOR",
        _t305.her_bakiyede_bar_geciliyor_mu() is True)
kontrol("madde 305: YALNIZ sart 4 dusuyor",
        _t305.yalniz_sart4_mu_dusuyor() is True)
kontrol("madde 305: sart 4 sicili DORT adaya cikti",
        _t305.sart4_kacinci_aday() == 4
        and set(_t305.SART4_SICIL) == {288, 290, 298, 305})
kontrol("madde 305: evren maliyeti YAPILANDIRMAYA bagli cikti",
        _t305.evren_maliyeti_yapilandirmaya_bagli_mi() is True
        and abs(_t305.OLCULEN_13X3 + 9.83) < 0.01)
kontrol("madde 305: olculen kayip madde 295'in basamagindan KUCUK",
        abs(_t305.OLCULEN_13X3) < abs(_ee300.evren_maliyeti(20.51)))
kontrol("madde 305: KAR D2 neti, TAM eksi olculen kayba esit",
        abs((_t305.KOLLAR["KAR TAM"][6] + _t305.OLCULEN_13X3)
            - _t305.KOLLAR["KAR D2"][6]) < 0.01)
kontrol("madde 305: madde 304'un merdiveni 13x3'u KOTU gosteriyor",
        _t305.madde304_kitabi_kotu_mu_gosteriyor() is True
        and abs(_t305.MADDE304_SAPMASI - 3.53) < 0.01)
kontrol("madde 304 dosyasi madde 305'e ILERI ISARET veriyor",
        hasattr(_sm304, "MADDE305_NOTU")
        and "MADDE 305 DUZELTMESI" in _sm304.MADDE305_NOTU
        and _sm304.MADDE305_OLCULEN_13X3["D2"] == 185.50)
kontrol("madde 305: sleeve REZERV=0 ve gerekcesi madde 299'a dayaniyor",
        _t305.SLEEVE_REZERV == 0 and "299" in _t305.SLEEVE_REZERV_GEREKCE)
kontrol("madde 305: eleme CIKTIDAN dogrulandi",
        "9/9" in _t305.ELEME_DOGRULANDI and "2/2" in _t305.ELEME_DOGRULANDI)
kontrol("madde 305: ayar DEGISMEDI",
        _t305.ayar_degisti_mi() is False
        and "13 dilim x 3 bacak" in _t305.ONERI)
kontrol("madde 305: uc yasa da yazili",
        "ANA KITABIN dozuna" in _t305.YASA1
        and "bacaklari FARKLI" in _t305.YASA2
        and "yapilandirmaya bagli" in _t305.YASA3)
kontrol("kâr haritası madde 305'i cesitlendirici-doz yasasi olarak yazdi",
        "Madde 305" in _harita and "ANA KİTABIN DOZUNA" in _harita)
kontrol("README madde 305'i tasiyor",
        "## 305." in _readme297 and "+12,69" in _readme297)
kontrol("NEREDE_NE_VAR madde 305'in satirini tasiyor",
        "| **305** |" in _nerede297)

# ───────────── MADDE 329: KOSULAN KITABIN DEVRE KESICISI
# (madde 335'te transkriptten geri kuruldu)
import arastirma_devre_kesici_kosulan as A329

kontrol("329: anahtar YANLIS kitabi gosteriyordu (15x5 vs 15x4)",
        A329.anahtar_yanlis_kitabi_mi_gosteriyordu()
        and A329.ESKI["anahtar"] == "15x5"
        and A329.KOSULAN["anahtar"] == "15x4")
kontrol("329: 2.000 $'da KOSULAN bacak sayisi 4 (yapilandirilan 5)",
        cb.uygun_bacak_sayisi(2000.0) == 4 and cb.N_LEGS == 5)
kontrol("329: kitap_anahtari(bakiye=2000) KOSULANI verir",
        cr.kitap_anahtari(bakiye=2000.0) == "15x4"
        and cr.kitap_anahtari() == "15x5")
kontrol("329: pay NEGATIFTI (-1,91 puan): esik < kitabin dususu",
        A329.pay_negatif_miydi() and abs(A329.PAY_ESKI + 1.91) < 1e-9)
kontrol("329: kademe 'olculmus' diyordu, yani UYARI basmiyordu",
        A329.kademe_yanlis_guven_veriyor_muydu())
kontrol("329: DURDUR (-23), kosulan kitabin INCELE seviyesindeydi",
        A329.durdur_incele_seviyesinde_miydi())
kontrol("329: kanonik yontem madde 231/303 ile BIREBIR",
        A329.kanonik_yontem_birebir_mi())
kontrol("329: en kotu rejim 'dusuk' (p5 -22,83)",
        A329.en_kotu_rejim_dusuk_mu()
        and abs(A329.REJIM_15X4["dusuk"][1] + 22.83) < 1e-9)
kontrol("329: KITAP_ESIK['15x4'] = (-0,23, -0,30) YAZILDI",
        cr.KITAP_ESIK["15x4"] == (-0.23, -0.30)
        and _re303.ESIK_KANONIK["15x4"] == (-0.23, -0.30))
kontrol("329: rejim olcumu de kaydedildi",
        cr.KITAP_REJIM_OLCUMU["15x4"][0] == "dusuk prim"
        and abs(cr.KITAP_REJIM_OLCUMU["15x4"][1] + 22.83) < 1e-9)
kontrol("329: kosulan kitapla kademe HALA 'olculmus'",
        cr.esik_kademesi("15x4") == "olculmus")
kontrol("329: pay DUZELDI (+3,09 puan)",
        A329.pay_duzeldi_mi() and abs(A329.PAY_YENI - 3.09) < 1e-9)
kontrol("329: KITAP_DUSUS'e KARISTIRILMADI (madde 295 tablosu bozulmaz)",
        A329.karistirilmadi_mi() and "15x4" not in cr.KITAP_DUSUS
        and "15x4" in cr.KITAP_DUSUS_KOSULAN)
kontrol("329: kosulan dusus tablosu bagimliligi (bakiye, evren) tasir",
        cr.KITAP_DUSUS_KOSULAN["15x4"][0] == 2000.0
        and cr.KITAP_DUSUS_KOSULAN["15x4"][1] == "D8")
kontrol("329: backtest_maksimumu KOSULAN tablodan okur (19,91)",
        abs(cr.backtest_maksimumu("15x4") - 19.91) < 1e-9
        and abs(cr.backtest_maksimumu("15x5") - 14.54) < 1e-9)
kontrol("329: ayni dusus (-%21) 2.000 $'da DEVAM, 20.000 $'da INCELE",
        cr.karar({"gun": 40, "dusus": -0.21, "ilk_bakiye": 2000.0},
                 {"durum": "YETERSİZ"}, {}, {})[0] == "DEVAM"
        and cr.karar({"gun": 40, "dusus": -0.21, "ilk_bakiye": 20000.0},
                     {"durum": "YETERSİZ"}, {}, {})[0] == "İNCELE")
kontrol("329: canli_gecer_mi(bakiye) L4'u KOSULAN kitaptan turetir",
        _ckr.canli_gecer_mi(30, dusus=24.0, bakiye=2000.0)["sartlar"]
        ["L4 dusus zarfi"][0] == _ckr.INCELE
        and _ckr.canli_gecer_mi(30, dusus=31.0, bakiye=2000.0)["sartlar"]
        ["L4 dusus zarfi"][0] == _ckr.DURDUR)
kontrol("329: bakiye VERILMEZSE madde 231'in cifti BIREBIR korunur",
        _ckr.canli_gecer_mi(30, dusus=24.0)["sartlar"]
        ["L4 dusus zarfi"][0] == _ckr.DURDUR
        and _ckr.DUSUS_INCELE == 18.0 and _ckr.DUSUS_DURDUR == 23.0)
kontrol("329: kayan seviyede ZARF OLASILIGI basilmaz (OLCULMEDI yazar)",
        "OLCULMEDI" in _ckr.canli_gecer_mi(30, dusus=31.0, bakiye=2000.0)
        ["sartlar"]["L4 dusus zarfi"][1])
kontrol("329: --bakiye bayragi CLI'da var",
        "--bakiye" in open(os.path.join(R, "canli_karar.py"),
                           encoding="utf-8").read())
kontrol("329: ACIK EKSEN yazili (evren sermayeye bagli)",
        "SERMAYEYE" in A329.ACIK_EKSEN.upper()
        and "YAPILMADI" in A329.ACIK_EKSEN)
kontrol("329: AYAR DEGISTI ama getiri iyilestirmesi DEGIL",
        A329.hukum()["ayar_degisti_mi"] is True
        and "yanlis alarm" in A329.hukum()["degisikligin_turu"])
kontrol("329: dosya TRANSKRIPTTEN yeniden yazildigini SOYLUYOR",
        A329.YENIDEN_YAZILDI is True
        and "ORIJINAL DEGIL" in A329.YENIDEN_YAZMA_NOTU)

print("\n7) PREFLIGHT ÖZETİ DOĞRU KARAR VERİYOR")
pf._sayac.update({pf.TAMAM: 3, pf.UYARI: 0, pf.HATA: 0}); pf._satirlar.clear()
kontrol("hata yoksa çıkış kodu 0", pf.yaz_ozet() == 0)
pf._sayac.update({pf.TAMAM: 1, pf.UYARI: 0, pf.HATA: 1})
pf._satirlar.clear(); pf._satirlar.append(("test", pf.HATA, "sebep"))
kontrol("hata varsa çıkış kodu 1", pf.yaz_ozet() == 1)

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum preflight testleri gecti.")
print("""
NE DOGRULANDI: preflight'in madde 204-216 arizalarini yakaladigi, VE
`CANLIYA_CIKIS.md` belgesindeki sayilarin KODLA ayni oldugu.

NEDEN IKINCISI: bayat bir TALIMAT, bayat bir AYARDAN daha tehlikelidir -
ayari kod denetler, talimati kimse denetlemez. Madde 217'de belge madde
182'nin curutulmus rakamlarini tasiyordu ve bacak formulu 3 kat
yanlisti. Artik bir ayar degisirse bu test kirilir.
""")
