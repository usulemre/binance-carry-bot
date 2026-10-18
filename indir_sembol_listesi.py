#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TAM SEMBOL LİSTESİNİ data.binance.vision S3 LİSTELEMESİNDEN ÜRETİR.

MADDE 335: `indir_genis.py` ve kardeşleri `/tmp/tum_semboller.txt`
okuyor; o dosya 2026-10-19'daki konteyner kaybında gitti ve projede
yoktu. Madde 253'ün `YENIDEN_KURMA` tarifi listeyi "S3 listelemesi,
CommonPrefixes" diye anlatıyor ama betiği projede yoktu. Artık var.

Çıktı iki yere yazılır:
    tum_semboller.txt       (PROJE içinde - kalıcı, git'te)
    /tmp/tum_semboller.txt  (indiricilerin okudugu yer)

KULLANIM
    python indir_sembol_listesi.py
"""
from __future__ import annotations

import os
import re
import sys
import urllib.request

KOK = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
# MADDE 335: listeleme XML'i data.binance.vision koklerinde DEGIL
# (orada HTML bir sayfa var); S3 ucundan alinir. Indirme ise
# data.binance.vision uzerinden yapilir - ikisi ayri.
ONEK = "data/futures/um/monthly/klines/"
R = os.path.dirname(os.path.abspath(__file__))


def listele() -> list[str]:
    semboller, imlec = [], None
    while True:
        u = f"{KOK}/?delimiter=/&prefix={ONEK}"
        if imlec:
            u += "&marker=" + urllib.request.quote(imlec, safe="")
        x = urllib.request.urlopen(u, timeout=60).read().decode()
        p = re.findall(r"<Prefix>" + re.escape(ONEK) + r"([^/<]+)/</Prefix>", x)
        if not p:
            break
        semboller += p
        print("  +%d (toplam %d) son: %s" % (len(p), len(semboller), p[-1]),
              flush=True)
        if "<IsTruncated>true</IsTruncated>" not in x:
            break
        imlec = ONEK + p[-1] + "/"
    return sorted(set(semboller))


if __name__ == "__main__":
    s = listele()
    usdt = [x for x in s if x.endswith("USDT")]
    print("toplam %d sembol, USDT-M %d" % (len(s), len(usdt)))
    for yol in (os.path.join(R, "tum_semboller.txt"), "/tmp/tum_semboller.txt"):
        with open(yol, "w", encoding="utf-8") as fh:
            fh.write("\n".join(usdt) + "\n")
        print("yazildi:", yol)
    sys.exit(0 if len(usdt) > 300 else 1)
