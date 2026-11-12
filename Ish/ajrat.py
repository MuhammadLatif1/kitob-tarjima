"""Butun .docx dagi har xatboshini nomerlangan birlik sifatida Ish/matn.json va Ish/meta.json ga chiqaradi.

Ishlatish: python Ish/ajrat.py Asl/<fayl>.docx

Belgilar:
  ⟦sN⟧...⟦/sN⟧  boshqa uslubdagi (qalin, kursiv, indeks va h.k.) oraliq
  ⟦hN⟧...⟦/hN⟧  giperhavola oralig'i
  ⟦x:N⟧         matn bo'lmagan element (rasm, sahifa uzilishi va h.k.)
  ⟦br⟧          qator uzilishi
  ⟦tab⟧         tabulyatsiya
"""
import sys
import zipfile
from collections import Counter, OrderedDict

from lxml import etree

from umumiy import ISH, MATNLI_QISMLAR, WQ, saqla

TASHLANADI = {"lastRenderedPageBreak", "proofErr", "rsid"}


def lname(el):
    return etree.QName(el).localname


def rpr_str(r):
    rpr = r.find(WQ + "rPr")
    return etree.tostring(rpr, encoding="unicode") if rpr is not None else ""


def run_bilan(r, child):
    """Faqat rPr va bitta bola elementdan iborat run nusxasi (XML matn)."""
    nr = etree.Element(WQ + "r")
    rpr = r.find(WQ + "rPr")
    if rpr is not None:
        nr.append(etree.fromstring(etree.tostring(rpr)))
    nr.append(etree.fromstring(etree.tostring(child)))
    return etree.tostring(nr, encoding="unicode")


def xatboshi(p):
    items = []  # (tur, qiymat, fmt, hl)
    bm_bosh, bm_oxir = [], []
    hls = []
    fld = None  # {'instr': str, 'holat': 'instr'|'natija', 'hl': idx}
    joriy_hl = [None]

    def qosh(item):
        items.append(item)

    def bookmark(el):
        (bm_oxir if items else bm_bosh).append(etree.tostring(el, encoding="unicode"))

    def run(r):
        nonlocal fld
        fmt = rpr_str(r)
        for c in r:
            n = lname(c)
            if n == "rPr" or n in TASHLANADI:
                continue
            hl = fld["hl"] if fld and fld["holat"] == "natija" else joriy_hl[0]
            if n == "fldChar":
                t = c.get(WQ + "fldCharType")
                if t == "begin":
                    fld = {"instr": "", "holat": "instr", "hl": None, "begin": run_bilan(r, c)}
                elif t == "separate" and fld:
                    hls.append({"tur": "fld", "instr": fld["instr"], "begin": fld["begin"]})
                    fld["hl"] = len(hls) - 1
                    fld["holat"] = "natija"
                elif t == "end":
                    fld = None
                continue
            if n == "instrText":
                if fld:
                    fld["instr"] += c.text or ""
                continue
            if fld and fld["holat"] == "instr":
                continue
            if n == "t":
                qosh(("t", c.text or "", fmt, hl))
            elif n == "tab":
                qosh(("tok", "⟦tab⟧", fmt, hl))
            elif n == "br" and not c.attrib:
                qosh(("tok", "⟦br⟧", fmt, hl))
            else:
                qosh(("obj", run_bilan(r, c), fmt, hl))

    for c in p:
        n = lname(c)
        if n == "pPr" or n in TASHLANADI:
            continue
        if n in ("bookmarkStart", "bookmarkEnd"):
            bookmark(c)
        elif n == "r":
            run(c)
        elif n == "hyperlink":
            hls.append({"tur": "el", "attrs": dict(c.attrib)})
            joriy_hl[0] = len(hls) - 1
            for cc in c:
                if lname(cc) == "r":
                    run(cc)
                elif lname(cc) in ("bookmarkStart", "bookmarkEnd"):
                    bookmark(cc)
            joriy_hl[0] = None
        else:
            items.append(("obj", etree.tostring(c, encoding="unicode"), "", joriy_hl[0]))

    # asosiy uslub: eng ko'p harf egallagan uslub
    cnt = Counter()
    for tur, v, fmt, hl in items:
        if tur == "t":
            cnt[fmt] += len(v.strip())
    asos = cnt.most_common(1)[0][0] if cnt and cnt.most_common(1)[0][1] > 0 else ""
    fmts = []
    objs = []
    out = []
    cur_hl, cur_f = None, None

    def fidx(fmt):
        if fmt == asos:
            return None
        if fmt not in fmts:
            fmts.append(fmt)
        return fmts.index(fmt) + 1

    for tur, v, fmt, hl in items:
        f = None
        if tur == "t":
            f = None if not v.strip() else fidx(fmt)
        if hl != cur_hl:
            if cur_f is not None:
                out.append("⟦/s%d⟧" % cur_f)
                cur_f = None
            if cur_hl is not None:
                out.append("⟦/h%d⟧" % (cur_hl + 1))
            if hl is not None:
                out.append("⟦h%d⟧" % (hl + 1))
            cur_hl = hl
        if tur == "t" and v.strip() == "" and cur_f is not None:
            f = cur_f  # bo'shliqni joriy oraliq ichida qoldiramiz
        if tur != "t":
            f = cur_f if tur == "tok" else None
        if f != cur_f:
            if cur_f is not None:
                out.append("⟦/s%d⟧" % cur_f)
            if f is not None:
                out.append("⟦s%d⟧" % f)
            cur_f = f
        if tur == "t":
            out.append(v)
        elif tur == "tok":
            out.append(v)
        else:
            objs.append(v)
            out.append("⟦x:%d⟧" % len(objs))
    if cur_f is not None:
        out.append("⟦/s%d⟧" % cur_f)
    if cur_hl is not None:
        out.append("⟦/h%d⟧" % (cur_hl + 1))
    matn = "".join(out)
    meta = {"asos": asos, "uslublar": fmts, "havolalar": hls, "obyektlar": objs,
            "bm_bosh": bm_bosh, "bm_oxir": bm_oxir}
    return matn, meta


def main():
    if len(sys.argv) != 2:
        sys.exit("Ishlatish: python Ish/ajrat.py Asl/<fayl>.docx")
    docx = sys.argv[1]
    matn = OrderedDict()
    meta = {"fayl": docx, "birliklar": {}}
    uid = 0
    with zipfile.ZipFile(docx) as z:
        qismlar = [n for n in z.namelist() if MATNLI_QISMLAR.match(n)]
        qismlar.sort(key=lambda n: (n != "word/document.xml", n))
        for q in qismlar:
            root = etree.fromstring(z.read(q))
            for i, p in enumerate(root.iter(WQ + "p")):
                uid += 1
                m, mt = xatboshi(p)
                ppr = p.find(WQ + "pPr")
                st = ppr.find(WQ + "pStyle") if ppr is not None else None
                mt.update({"qism": q, "indeks": i,
                           "uslub": st.get(WQ + "val") if st is not None else "",
                           "sahifa_uzilishi": ppr is not None and ppr.find(WQ + "pageBreakBefore") is not None})
                matn[str(uid)] = m
                meta["birliklar"][str(uid)] = mt
    saqla(ISH / "matn.json", matn)
    saqla(ISH / "meta.json", meta)
    print("Birliklar: %d (%s)" % (uid, ", ".join(qismlar)))


if __name__ == "__main__":
    main()
