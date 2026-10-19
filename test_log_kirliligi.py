"""MADDE 344 regresyon testi: main.py'yi import etmek bot.log AÇMAMALI.

Madde 343'te 'eldeki tek canlı kayıt' diye arşivlenen dosya, aslında
test koşularının bot.log'a sızan çıktısıydı (48 koşu x aynı 12 satır).
Sebep: main.py logging.FileHandler'ı import anında kuruyordu.
"""
import logging
import os
import subprocess
import sys
import tempfile

KOK = os.path.dirname(os.path.abspath(__file__))

with tempfile.TemporaryDirectory() as d:
    kod = (
        "import sys, logging; sys.path.insert(0, %r); import main; "
        "print(any(isinstance(h, logging.FileHandler) "
        "for h in logging.getLogger().handlers))" % KOK
    )
    r = subprocess.run([sys.executable, "-c", kod], cwd=d,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr[-2000:]
    assert r.stdout.strip().endswith("False"), \
        "main import edilince FileHandler kuruldu: " + r.stdout
    assert not os.path.exists(os.path.join(d, "bot.log")), \
        "main import edilince bot.log oluştu"

print("test_log_kirliligi: OK (main import'u log dosyası açmıyor)")
