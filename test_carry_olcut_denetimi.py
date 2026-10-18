"""MADDE 232 TESTLERI: funding beklentisi + rejim gostergesi.

Bu dosyanin varlik sebebi: rapor, beklenen funding'i `BEKLENEN_GUNLUK x
0.94` diye TURETIYORDU. O 0,94 madde 136'nin "funding gelirinin %94'u
LONG bacaktan" cumlesinden gelen bir ETIKET HATASIydi. Sonuc: SAGLIKLI
bir bot dusuk prim rejiminde DURDUR aliyordu - ve hata su an yuksek prim
rejimi tarafindan maskeleniyor.
"""
import sys

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad} {detay}")
        basarisiz.append(ad)


import carry_rapor as cr

print("1) BEKLENEN FUNDING OLCULDU, TURETILMEDI")
kontrol("BEKLENEN_FUNDING_GUNLUK var", hasattr(cr, "BEKLENEN_FUNDING_GUNLUK"))
kontrol("BEKLENEN_FUNDING_TABAN var", hasattr(cr, "BEKLENEN_FUNDING_TABAN"))
_kaynak = open(cr.__file__, encoding="utf-8").read()
# Formulun KENDISI docstring'de KASTEN duruyor (neyin yanlis oldugunun
# kaydi). O yuzden CALISTIRILABILIR kodu ayiklayip oraya bakmak gerekir -
# madde 217'de belge testinde de ayni tuzak vardi (`_govde`).
import ast as _ast
_agac = _ast.parse(_kaynak)
for _n in _ast.walk(_agac):          # docstring'leri bosalt
    if isinstance(_n, _ast.Constant) and isinstance(_n.value, str):
        _n.value = ""
_kod = _ast.unparse(_agac)
kontrol("eski TURETME formulu CALISTIRILABILIR kodda YOK",
        "0.94" not in _kod and "BEKLENEN_GUNLUK * 0.94" not in _kod,
        "(formul hala kodda)")
kontrol("funding beklentisi artik TABAN sabitinden geliyor",
        "BEKLENEN_FUNDING_TABAN" in _kod)
_satir = [s for s in _kaynak.splitlines()
          if s.strip().startswith("bekl = ")]
kontrol("bekl satiri tek ve TABAN kullaniyor",
        len(_satir) == 1 and "BEKLENEN_FUNDING_TABAN" in _satir[0],
        f"({_satir})")
kontrol("etiket hatasi KAYITTA (madde 136 vs rapor)",
        "ETİKET" in _kaynak and "madde 136" in _kaynak
        and "LONG bacaktan" in _kaynak)
kontrol("docstring artik 'gelirin %94'u funding'den' DEMIYOR",
        "gelirin ~%94'ü funding'den" not in _kaynak)

print("\n2) OLCULEN DEGERLER TUTARLI")
kontrol("taban < harman < yuksek",
        cr.BEKLENEN_FUNDING_TABAN < cr.BEKLENEN_FUNDING_GUNLUK
        < cr.BEKLENEN_FUNDING_YUKSEK,
        f"({cr.BEKLENEN_FUNDING_TABAN}, {cr.BEKLENEN_FUNDING_GUNLUK}, "
        f"{cr.BEKLENEN_FUNDING_YUKSEK})")
# eski formulun sagliklı botu nasil cezalandirdigi - regresyon kaydi
_eski = 0.002163 * 0.94
kontrol("eski formul olculenden >1,5 KAT yuksekti (hatanin buyuklugu)",
        _eski / cr.BEKLENEN_FUNDING_GUNLUK > 1.5,
        f"({_eski / cr.BEKLENEN_FUNDING_GUNLUK:.2f}x)")
kontrol("eski formulle DUSUK prim rejimi DURDUR aliyordu",
        cr.BEKLENEN_FUNDING_TABAN / _eski < cr.FUNDING_ORAN_DURDUR,
        f"(oran {cr.BEKLENEN_FUNDING_TABAN / _eski:.2f})")
kontrol("YENI tabanla her rejim TEMIZ okur (yanlis alarm yok)",
        all(v / cr.BEKLENEN_FUNDING_TABAN >= cr.FUNDING_ORAN_INCELE
            for v in (cr.BEKLENEN_FUNDING_TABAN, cr.BEKLENEN_FUNDING_GUNLUK,
                      cr.BEKLENEN_FUNDING_YUKSEK)))
kontrol("GERCEK ariza (tahsilatin yarisi) hala DURDUR verir",
        (cr.BEKLENEN_FUNDING_TABAN * 0.4) / cr.BEKLENEN_FUNDING_TABAN
        < cr.FUNDING_ORAN_DURDUR)

print("\n3) REJIM GOSTERGESI")
kontrol("dusuk rejim ortalamasi DUSUK PRIM der",
        cr.rejim_tahmini(cr.BEKLENEN_FUNDING_TABAN)[0] == "DÜŞÜK PRİM")
kontrol("harman HARMAN/ARADA der",
        cr.rejim_tahmini(cr.BEKLENEN_FUNDING_GUNLUK)[0] == "HARMAN/ARADA")
kontrol("yuksek rejim ortalamasi YUKSEK PRIM der",
        cr.rejim_tahmini(cr.BEKLENEN_FUNDING_YUKSEK)[0] == "YÜKSEK PRİM")
kontrol("rejim -> beklenti esleme madde 231'in sayilari",
        cr.rejim_tahmini(cr.BEKLENEN_FUNDING_TABAN)[1] == 95.0
        and cr.rejim_tahmini(cr.BEKLENEN_FUNDING_YUKSEK)[1] == 141.0)
kontrol("sinirlar MONOTON (dusuk<harman<yuksek siralamasi bozulmuyor)",
        [cr.rejim_tahmini(v)[1] for v in
         (0.0003, cr.BEKLENEN_FUNDING_TABAN, cr.BEKLENEN_FUNDING_GUNLUK,
          cr.BEKLENEN_FUNDING_YUKSEK, 0.004)] == [95.0, 95.0, 112.5, 141.0, 141.0])
kontrol("rapor metni REJIM satirini yaziyor", "REJİM" in _kaynak
        and "geçerli beklenti" in _kaynak)

print("\n4) MADDE 233 - IZLEME ARACI TEK KANONIK KAYNAGI KULLANIYOR")
import carry_izleme as cz
kontrol("carry_izleme funding beklentisini carry_rapor'dan aliyor",
        cz.BEKLENEN_FUNDING_TABAN == cr.BEKLENEN_FUNDING_TABAN
        and cz.BEKLENEN_FUNDING_GUNLUK == cr.BEKLENEN_FUNDING_GUNLUK)
_iz = open(cz.__file__, encoding="utf-8").read()
kontrol("izleme ALARMI mutlak olcute bagli, orana DEGIL",
        "BEKLENEN_FUNDING_TABAN" in _iz and "gunluk / BEKLENEN_FUNDING_TABAN" in _iz)
import ast as _a2
_ag = _a2.parse(_iz)
for _n in _a2.walk(_ag):
    if isinstance(_n, _a2.Constant) and isinstance(_n.value, str):
        _n.value = ""
_izkod = _a2.unparse(_ag)
kontrol("eski oran alarmi (pay < PAYI*0.5) CALISTIRILABILIR kodda YOK",
        "BEKLENEN_FUNDING_PAYI * 0.5" not in _izkod
        and "PAYI * 0.5" not in _izkod)
kontrol("oran yine YAZDIRILIYOR ama 'karar olcutu DEGIL' diye",
        "KARARSIZ" in _iz and "karar ölçütü DEĞİL" in _iz)
kontrol("oranin KARARSIZLIGI sayilarla kayitta (p95 7,49 / %26 oten ay)",
        "7,49" in _iz and "%26" in _iz)

print("\n5) MADDE 233 - DUSUS ESIKLERI EN KOTU REJIME GORE")
kontrol("INCELE esigi dusuk prim p5'ini (-%17,9) KAPSIYOR",
        cr.DUSUS_INCELE * 100 <= -17.9 + 0.3,
        f"({cr.DUSUS_INCELE})")
kontrol("DURDUR esigi dusuk prim p1'ini (-%22,3) KAPSIYOR",
        cr.DUSUS_DURDUR * 100 <= -22.3 + 0.8, f"({cr.DUSUS_DURDUR})")
kontrol("INCELE, DURDUR'dan SIG", cr.DUSUS_INCELE > cr.DUSUS_DURDUR)
kontrol("madde 175'in curutulmus esikleri ARTIK KULLANILMIYOR",
        cr.DUSUS_INCELE != -0.20 and cr.DUSUS_DURDUR != -0.25)

print("\n" + "=" * 62)
if basarisiz:
    print(f"BASARISIZ: {len(basarisiz)}")
    for t in basarisiz:
        print(f"  - {t}")
    sys.exit(1)
print("Tum madde 232-233 olcut denetimi testleri gecti.")
print("""
NE DOGRULANDI: beklenen funding'in TURETILMEDIGI, etiket hatasinin
kayitta oldugu, yeni tabanla hicbir rejimin yanlis alarm vermedigi ama
gercek arizanin hala yakalandigi, ve rejim gostergesinin madde 231'in
sayilarini dogru esledigi.

NE DOGRULANMADI: 0,1055%/gun rakaminin CANLIDA tutacagi. O, gun 14'te
%100 guclu olan olcumun ta kendisi (madde 216) - zaten onu dogrulamak
icin var.
""")
