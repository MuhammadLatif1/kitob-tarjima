"""Ish/tarjima.json dagi tarjimani .docx nusxasiga joylaydi.

Ishlatish: python Ish/joyla.py Tarjima/<asl_nom>_uz.docx

Faqat tarjimasi bor xatboshilar qayta quriladi: pPr (uslub, sahifa sozlamalari) tegilmaydi,
rasmlar, xatcho'plar, giperhavolalar Ish/meta.json dagi asl XML dan tiklanadi.
Boshqa barcha zip qismlari (word/media/ va h.k.) bayt-baayt ko'chiriladi.
"""
import re
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

from umumiy import ISH, WQ, XML_NS, yukla

TOKEN = re.compile(r"(⟦[^⟦⟧]*⟧)")


def el(xml):
    return etree.fromstring(xml)


def rpr(xml):
    return etree.fromstring(xml) if xml else None


def yangi_run(fmt_xml, matn=None, child=None):
    r = etree.Element(WQ + "r")
    x = rpr(fmt_xml)
    if x is not None:
        r.append(x)
    if matn is not None:
        t = etree.SubElement(r, WQ + "t")
        t.text = matn
        t.set("{%s}space" % XML_NS, "preserve")
    if child is not None:
        r.append(child)
    return r


def qayta_qur(p, tarjima, mt):
    for c in list(p):
        if etree.QName(c).localname != "pPr":
            p.remove(c)
    for x in mt["bm_bosh"]:
        p.append(el(x))
    asos = mt["asos"]
    fmt = asos
    konteyner = p
    fld_oxiri = False
    for tok in TOKEN.split(tarjima):
        if not tok:
            continue
        m = re.fullmatch(r"⟦(/?)([sh])(\d+)⟧", tok)
        if m:
            yop, tur, n = m.group(1), m.group(2), int(m.group(3))
            if tur == "s":
                fmt = asos if yop else mt["uslublar"][n - 1]
            else:
                h = mt["havolalar"][n - 1]
                if not yop:
                    if h["tur"] == "el":
                        hl = etree.SubElement(p, WQ + "hyperlink")
                        for k, v in h["attrs"].items():
                            hl.set(k, v)
                        konteyner = hl
                    else:
                        p.append(el(h["begin"]))
                        p.append(yangi_run("", child=_instr(h["instr"])))
                        p.append(yangi_run("", child=_fld("separate")))
                        fld_oxiri = True
                else:
                    if h["tur"] == "el":
                        konteyner = p
                    elif fld_oxiri:
                        p.append(yangi_run("", child=_fld("end")))
                        fld_oxiri = False
            continue
        if tok == "⟦br⟧":
            konteyner.append(yangi_run(fmt, child=etree.Element(WQ + "br")))
        elif tok == "⟦tab⟧":
            konteyner.append(yangi_run(fmt, child=etree.Element(WQ + "tab")))
        elif tok.startswith("⟦x:"):
            n = int(tok[3:-1])
            konteyner.append(el(mt["obyektlar"][n - 1]))
        elif tok.startswith("⟦"):
            raise ValueError("Noma'lum belgi: %s" % tok)
        else:
            konteyner.append(yangi_run(fmt, matn=tok))
    for x in mt["bm_oxir"]:
        p.append(el(x))


def _instr(s):
    e = etree.Element(WQ + "instrText")
    e.text = s
    e.set("{%s}space" % XML_NS, "preserve")
    return e


def _fld(t):
    e = etree.Element(WQ + "fldChar")
    e.set(WQ + "fldCharType", t)
    return e


def main():
    if len(sys.argv) != 2:
        sys.exit("Ishlatish: python Ish/joyla.py Tarjima/<asl_nom>_uz.docx")
    nusxa = Path(sys.argv[1])
    meta = yukla(ISH / "meta.json")
    tarj = yukla(ISH / "tarjima.json")
    asl = Path(meta["fayl"])
    if not nusxa.exists():
        nusxa.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(asl, nusxa)
    # qismlar bo'yicha guruhlash
    qismlar = {}
    for uid, t in tarj.items():
        mt = meta["birliklar"][uid]
        qismlar.setdefault(mt["qism"], []).append((mt["indeks"], t, mt))
    tmp = nusxa.with_suffix(".tmp.docx")
    with zipfile.ZipFile(nusxa) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename in qismlar:
                root = etree.fromstring(data)
                ps = list(root.iter(WQ + "p"))
                for idx, t, mt in qismlar[item.filename]:
                    qayta_qur(ps[idx], t, mt)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            zout.writestr(item, data)
    tmp.replace(nusxa)
    print("Joylandi: %d birlik -> %s" % (len(tarj), nusxa))


if __name__ == "__main__":
    main()
