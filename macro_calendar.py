"""
Makro Haber Saati Filtresi
=============================
2026 Eylül piyasa analizi: BTC'nin son dönemdeki en büyük hareketleri
(ör. bir haftada %24.8 - 2020'den beri en büyük haftalık hareketlerin
ilk %1'i) teknik kırılımlardan değil, FED açıklamaları ve enflasyon
verileri gibi PLANLI makro haberlerden kaynaklandı. Hiçbir teknik
indikatör bu türden haber bazlı ani hareketleri önceden tahmin edemez.

Bu yüzden en güvenli yaklaşım: yüksek etkili makro haber saatlerinin
ETRAFINDA yeni işlem AÇMAMAK (açık pozisyonları yönetmeye devam etmek
ayrı bir konu - onlar zaten SL/TP ile korunuyor).

KULLANIM: Aşağıdaki MACRO_EVENTS listesini güncel tutmanız gerekir.
Kaynak: https://www.forexfactory.com/calendar (yüksek etkili "Red" olaylar,
özellikle FOMC kararı, FOMC konuşmaları, CPI, NFP/istihdam verileri).
Bu liste ne otomatik güncellenir ne de botun içinde tahmin edilir -
gerçek tarihleri siz girmelisiniz.
"""

from datetime import datetime, timedelta, timezone

# Örnek format - GERÇEK tarihlerle güncelleyin (UTC, ISO format):
# MACRO_EVENTS = [
#     "2026-09-17T18:00:00",  # FOMC faiz kararı
#     "2026-10-15T12:30:00",  # CPI enflasyon verisi
# ]
MACRO_EVENTS: list[str] = [
    # Buraya bilinen üst düzey makro haber tarihlerini ekleyin.
]

AVOID_HOURS_BEFORE = 2   # Haberden bu kadar saat önce yeni işlem açma
AVOID_HOURS_AFTER = 4    # Haberden sonra bu kadar saat (ilk volatilite dalgası geçsin)


def is_configured() -> bool:
    """Makro takvim DOLDURULMUŞ mu?

    MACRO_EVENTS boşsa filtre sessizce hiçbir şey yapmaz - bot "makro
    korumam var" sanır ama yoktur. Bu fonksiyon durumu görünür kılar;
    main.py başlangıçta uyarı basar.
    """
    return len(MACRO_EVENTS) > 0


def gecmis_olaylari_temizle() -> int:
    """Tarihi geçmiş olayları listeden çıkarır, kaç tane silindiğini döner.

    Liste elle güncellendiği için eski tarihler birikir. Bunlar zararsız
    ama listeyi okunmaz hale getirir ve "güncel mi?" sorusunu zorlaştırır.
    """
    global MACRO_EVENTS
    simdi = datetime.now(timezone.utc)
    once = len(MACRO_EVENTS)
    kalan = []
    for e in MACRO_EVENTS:
        try:
            t = datetime.fromisoformat(e)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            if t + timedelta(hours=AVOID_HOURS_AFTER) >= simdi:
                kalan.append(e)
        except ValueError:
            # Bozuk tarih formatı - listede bırakma, ama sessizce yutma
            continue
    MACRO_EVENTS = kalan
    return once - len(kalan)


def is_near_macro_event(now: datetime = None) -> tuple[bool, str]:
    """(True, sebep) döner eğer şu an bir makro habere çok yakınsa,
    aksi halde (False, '') döner. `now` verilmezse mevcut UTC zamanı kullanılır.

    BOZUK TARİH TOLERANSI: listedeki geçersiz bir tarih formatı botu
    çökertmemeli - o girdi atlanır ve diğerleri kontrol edilir."""
    if now is None:
        now = datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    for event_str in MACRO_EVENTS:
        try:
            event_time = datetime.fromisoformat(event_str)
        except ValueError:
            continue   # bozuk girdi - botu çökertme, atla
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        window_start = event_time - timedelta(hours=AVOID_HOURS_BEFORE)
        window_end = event_time + timedelta(hours=AVOID_HOURS_AFTER)

        if window_start <= now <= window_end:
            return True, f"Makro haber penceresi: {event_time.isoformat()}"

    return False, ""
