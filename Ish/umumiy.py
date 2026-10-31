"""Skriptlar uchun umumiy yordamchi funksiyalar."""
import json
import re
from pathlib import Path

ISH = Path(__file__).resolve().parent
LOYIHA = ISH.parent
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
WQ = "{%s}" % W
XML_NS = "http://www.w3.org/XML/1998/namespace"
MATNLI_QISMLAR = re.compile(r"^word/(document|footnotes|endnotes|header\d*|footer\d*)\.xml$")

BELGI = re.compile(r"⟦[^⟦⟧]*⟧")
HARF = re.compile(r"[A-Za-z]")


def yukla(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def saqla(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    tmp.replace(path)


def belgilar(s):
    return BELGI.findall(s)


def toza(s):
    """Belgilarsiz sof matn."""
    return BELGI.sub(" ", s)


def tarjima_kerak(s):
    return bool(HARF.search(toza(s)))


def raqamlar(s):
    return re.findall(r"\d+(?:[.,]\d+)*", toza(s))
