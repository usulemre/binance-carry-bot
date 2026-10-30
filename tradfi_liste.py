"""TradFi perp sembolleri — `carry_bot._TRADFI_YEDEK`'ten TÜRETİLİR.

MADDE 335: orijinal `tradfi_liste.py` 2026-10-19'daki konteyner
kaybında gitti ve proje arşivinde yoktu. Ama liste aslında **iki yerde**
duruyordu: canlı bot kendi içinde `_TRADFI_YEDEK` olarak taşıyor
(exchange_info alınamadığında kullanılan yedek). Bu dosya artık o tek
kaynaktan okur — kopya tutmaz, yani ikisi bir daha AYRIŞAMAZ.

Not: canlıda asıl tespit `tradfi_mi()` ile exchange_info'nun
`underlyingType` alanından yapılır; bu liste onun yedeği ve geri testin
tek bilgi kaynağı (geri testte exchange_info yoktur).
"""
from carry_bot import _TRADFI_YEDEK as _Y

import os as _os
TRADFI: set[str] = set(_Y)
# MADDE 675: araştırma eki — aylık veri paketinin exchangeInfo'sundan çıkan yeni TradFi perp'ler (bot bunları canlıda underlyingType ile eler)
_EK = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "tradfi_ek.txt")
if _os.path.exists(_EK):
    TRADFI |= set(open(_EK, encoding="utf-8").read().split())
TRADFI_YER_TUTUCU = False
KAYNAK = "carry_bot._TRADFI_YEDEK (tek kaynak, kopya YOK)"
