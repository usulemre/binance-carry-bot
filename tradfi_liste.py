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

TRADFI: set[str] = set(_Y)
TRADFI_YER_TUTUCU = False
KAYNAK = "carry_bot._TRADFI_YEDEK (tek kaynak, kopya YOK)"
