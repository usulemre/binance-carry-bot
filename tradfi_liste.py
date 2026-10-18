"""TradFi perp sembolleri (madde 335 YER TUTUCU).

*** DİKKAT: BU DOSYA ORİJİNAL DEĞİL. *** Orijinal `tradfi_liste.py`
2026-10-19'daki konteyner kaybında gitti ve proje arşivinde yoktu.
README (madde ~300 civarı) listeyi tarif ediyor ama sembolleri tek tek
saymıyor: "Binance Aralık 2025'ten itibaren yüzlerce TradFi perp
listeledi (XAU, CL, TSLA, NVDA, SPY, QQQ, SKHYNIX, SAMSUNG, HK/KR
hisseleri...). Panelde 150 tane."

NEDEN BOŞ BIRAKILDI: kurtarılan `data_genis/` 122 sembol içeriyor ve
ÖLÇÜLDÜ - hiçbiri 2025-12'den sonra listelenmemiş, yani bu evrende
TradFi sembolü YOK. Dolayısıyla boş küme, bu veri için orijinaliyle
AYNI sonucu verir. Geniş evren (847 sembol) geri getirilirse bu liste
YENİDEN ÜRETİLMELİDİR; aksi halde TradFi'ler sessizce evrene girer ve
madde ~300'ün ölçtüğü zarar (+%30,3 -> +%34,1 farkı) geri gelir.
"""
TRADFI: set[str] = set()
TRADFI_YER_TUTUCU = True
