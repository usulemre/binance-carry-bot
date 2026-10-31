#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 680 testleri: Ed25519 anahtarıyla imza (BINANCE_PRIVATE_KEY_PATH), HMAC'a sessiz düşüş yok, betik anahtar üretir."""
import base64, os, subprocess, sys, tempfile, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

T = tempfile.mkdtemp()
r = subprocess.run(["bash", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy/ed25519_anahtar.sh"), T],
                   capture_output=True, text=True)
F = os.path.join(T, "binance_ed25519.pem")
kontrol("betik anahtar üretti, izin 600", r.returncode == 0 and os.path.exists(F) and (os.stat(F).st_mode & 0o777) == 0o600, r.stderr)
acik = r.stdout.split("=== Binance'e yapıştırılacak AÇIK anahtar ===")[1].split("Özel")[0].strip()
kontrol("açık anahtar basıldı, özel anahtar BASILMADI", acik.startswith("-----BEGIN PUBLIC KEY") and "PRIVATE" not in r.stdout)
r2 = subprocess.run(["bash", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy/ed25519_anahtar.sh"), T], capture_output=True, text=True)
kontrol("ikinci çalıştırma var olan anahtarın üstüne yazmaz", "zaten var" in r2.stdout)

import exchange_client as X
os.environ.pop("BINANCE_PRIVATE_KEY_PATH", None)
c = X.ExchangeClient("K", "S", mode="demo"); kontrol("ayarsız: HMAC (eski yol)", c.imza == "hmac")
os.environ["BINANCE_PRIVATE_KEY_PATH"] = F
c = X.ExchangeClient("K", "", mode="demo")
kontrol("Ed25519 etkin, secret gerekmez", c.imza == "ed25519")
sig = urllib.parse.unquote(c.client._generate_signature({"symbol": "BTCUSDT", "timestamp": 1}))
# doğrulama pycryptodome ile (python-binance'in kendi bağımlılığı; ek paket gerekmez — CI'da 'cryptography' yok)
from Crypto.PublicKey import ECC
from Crypto.Signature import eddsa
try:
    eddsa.new(ECC.import_key(acik), "rfc8032").verify(b"symbol=BTCUSDT&timestamp=1", base64.b64decode(sig)); ok = True
except Exception:
    ok = False
kontrol("imza açık anahtarla doğrulanıyor", ok)
c = X.ExchangeClient("K", "S", mode="live"); kontrol("canlı modda da Ed25519", c.imza == "ed25519")
os.environ["BINANCE_PRIVATE_KEY_PATH"] = os.path.join(T, "yok.pem")
try:
    X.ExchangeClient("K", "S", mode="demo"); kontrol("dosya yoksa HATA (HMAC'a sessiz düşmez)", False)
except FileNotFoundError:
    kontrol("dosya yoksa HATA (HMAC'a sessiz düşmez)", True)
bozuk = os.path.join(T, "bozuk.pem"); open(bozuk, "w").write("merhaba")
os.environ["BINANCE_PRIVATE_KEY_PATH"] = bozuk
try:
    X.ExchangeClient("K", "S", mode="demo"); kontrol("PEM değilse HATA", False)
except ValueError:
    kontrol("PEM değilse HATA", True)
os.environ.pop("BINANCE_PRIVATE_KEY_PATH")
# madde 680: şifreli anahtarlar (systemd ImportCredential -> $CREDENTIALS_DIRECTORY/carry.env) config'e yüklenir
K = tempfile.mkdtemp(); open(os.path.join(K, "carry.env"), "w").write("BINANCE_API_KEY=SK\nBINANCE_API_SECRET=SS\n")
env = {k: v for k, v in os.environ.items() if not k.startswith("BINANCE_")}; env["CREDENTIALS_DIRECTORY"] = K
r = subprocess.run([sys.executable, "-c", "import config;print(config.API_KEY, config.API_SECRET)"], cwd=T, env={**env, "PYTHONPATH": os.path.dirname(os.path.abspath(__file__))},
                   capture_output=True, text=True)
kontrol("şifreli kimlik bilgisi config'e yüklenir", r.stdout.split() == ["SK", "SS"], r.stdout + r.stderr[-200:])
os.rename(os.path.join(K, "carry.env"), os.path.join(K, "carry-d1.env"))
r = subprocess.run([sys.executable, "-c", "import config;print(config.API_KEY)"], cwd=T, env={**env, "PYTHONPATH": os.path.dirname(os.path.abspath(__file__))},
                   capture_output=True, text=True)
kontrol("çoklu demo kimlik bilgisi (carry-AD.env)", r.stdout.strip() == "SK", r.stdout + r.stderr[-200:])
import nabiz
kl = os.path.join(T, "carry"); os.makedirs(kl); open(os.path.join(kl, "carry_bot.py"), "w").write("")
open(os.path.join(kl, ".env"), "w").write("BINANCE_MODE=demo\n# gizli satırlar şifrelendi: /etc/credstore.encrypted/carry.env (madde 680)\n")
sc = lambda k, s: "enabled" if k == "is-enabled" else "failed"
kontrol("nabız: şifreli kurulumu ATLAMAZ (izlemeye devam)", nabiz.kontrol(kl, "carry", sc) != [])
print(f"\nSONUÇ: {_h} hata")
sys.exit(1 if _h else 0)
