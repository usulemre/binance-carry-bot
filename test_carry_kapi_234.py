"""MADDE 234 TESTLERI: saglik kapisindan IC'nin cikarilmasi.

Bu dosyanin varlik sebebi: kapi, 4 yilda bir kez otmusti ve o otme
stratejinin +%25,5 yaptigi 36 gune denk geliyordu - yani kapi kitabi
en iyi doneminde kapatacakti. Sebep IC esigiydi ve IC'nin ileriye
donuk haber degeri OLCULDU: yok.
"""
import sys

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


import carry_saglik as CS

_S = [0.60] * 6          # saglikli IC
_F = [0.002] * 6         # saglikli F (20bp)
_D = [0.0015] * 6        # saglikli DISP (15bp)

print("1) IC ARTIK KAPIYI KAPATMIYOR")
d, g = CS.saglik_durumu([0.05] * 6, _F, _D)
kontrol("IC cokmesi (0,05) SAGLIKLI donuyor", d == "SAGLIKLI", f"({d}, {g})")
kontrol("ama UYARI olarak gerekceye yaziliyor", "UYARI" in g and "IC" in g, f"({g})")
kontrol("uyari 'kapatma olcutu DEGIL' diyor", "kapatma ölçütü DEĞİL" in g)
d, g = CS.saglik_durumu([0.0] * 6, _F, _D)
kontrol("IC tam SIFIR olsa bile kapatmiyor", d == "SAGLIKLI", f"({d})")
d, g = CS.saglik_durumu([-0.5] * 6, _F, _D)
kontrol("IC NEGATIF olsa bile kapatmiyor", d == "SAGLIKLI", f"({d})")

print("\n2) F VE DISP HALA KAPATIYOR (kapi dissiz kalmadi)")
d, g = CS.saglik_durumu(_S, [-0.001] * 6, _D)
kontrol("F <= 0 -> BOZUK", d == "BOZUK", f"({d})")
kontrol("gerekce funding gelirini soyluyor", "funding geliri" in g)
d, g = CS.saglik_durumu(_S, _F, [0.0001] * 6)
kontrol("DISP esigin altinda -> BOZUK", d == "BOZUK", f"({d})")
kontrol("gerekce funding farkini soyluyor", "funding farki" in g)
d, _ = CS.saglik_durumu(_S, [-0.001] * 6, [0.0001] * 6)
kontrol("ikisi birden bozuksa yine BOZUK", d == "BOZUK")
# IC uyarisi BOZUK gerekcesine de ekleniyor
d, g = CS.saglik_durumu([0.05] * 6, [-0.001] * 6, _D)
kontrol("BOZUK halde de IC uyarisi gerekceye ekleniyor",
        d == "BOZUK" and "UYARI" in g, f"({d}, {g})")

print("\n3) ISINMA DAVRANISI KORUNDU (madde 123/185)")
d, _ = CS.saglik_durumu([0.6] * 3, _F, _D)
kontrol("yetersiz gecmiste ISINMA", d == "ISINMA")
kontrol("ISINMA'da kapi ACIK varsayilir (kod yorumu)",
        "veri yokken durmak" in CS.saglik_durumu.__doc__)

print("\n4) OLCUM SONUCLARI KAYITTA (madde 234)")
_k = open(CS.__file__, encoding="utf-8").read()
kontrol("IC'nin haber degerinin YOK oldugu kayitta",
        "0,048" in _k and "p=0,067" in _k)
kontrol("esigin altinda getirinin DAHA IYI oldugu kayitta", "+%10,9" in _k)
kontrol("F ve DISP'in siraladigi kayitta", "0,314" in _k and "0,336" in _k)
kontrol("yanlis alarm olayi kayitta (+%25,5 / 95. yuzdelik)",
        "+%25,5" in _k and "95. yüzdeli" in _k)
kontrol("madde 139'un t=-0,55'i kayitta", "t=-0,55" in _k)
kontrol("madde 139.5'in '0 yanlis alarm' iddiasinin curudugu kayitta",
        "ÇÜRÜDÜ" in _k)
kontrol("IC'nin hala HESAPLANDIGI yaziyor",
        "hesaplanmaya ve raporlanmaya DEVAM" in _k)

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum madde 234 testleri gecti.")
print("""
NE DOGRULANDI: IC'nin kapiyi kapatmadigi, F ve DISP'in hala kapattigi,
ISINMA davranisinin korundugu ve olcumlerin kayitta oldugu.

NE DOGRULANMADI: senaryo A'yi (kalicilik olumu) kacirmanin bedeli. Madde
139 onu t=-0,55 ile ANLAMSIZ olcmustu; bu bir SECIM, kanitlanmis bir
bedava ogle yemegi degil. Olum senaryolari
`arastirma_kapi_olum.py` ile yeniden calistirilabilir: B 35 gun, C 140
gun (madde 139: 23-39 ve 138-183).
""")
