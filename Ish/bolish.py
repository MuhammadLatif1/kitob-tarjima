"""Boblar chegarasini aniqlaydi va Ish/boblar.json ga yozadi.

Ishlatish: python Ish/bolish.py

Tartib (CLAUDE.md 4.2):
 1) mundarija (giperhavolalar -> xatcho'plar) bo'yicha;
 2) mundarija bo'lmasa: sarlavha uslubi / pageBreakBefore / matn naqshlari.
Division/Section sarlavhalari va ularning kirish matni keyingi bobga qo'shiladi.
"""
import re

from lxml import etree

from umumiy import ISH, WQ, saqla, toza, yukla

BOB_NAQSH = re.compile(r"^\s*(chapter\s+\d+|part\s+\w+|\d+\.?\s+\S|[IVXLC]+\.\s+\S|"
                       r"preface|introduction|foreword|conclusion|epilogue|prologue|appendix|"
                       r"notes|bibliography|references|index|glossary|afterword)", re.I)
YUQORI = re.compile(r"^\s*(division|section)\s+\w+", re.I)


def anchor_of(havola):
    if havola["tur"] == "el":
        return havola["attrs"].get(WQ + "anchor")
    m = re.search(r'\\l\s+"([^"]+)"', havola.get("instr", ""))
    return m.group(1) if m else None


def bookmark_joylari(meta):
    joy = {}
    for uid, mt in meta["birliklar"].items():
        for x in mt["bm_bosh"] + mt["bm_oxir"]:
            el = etree.fromstring(x)
            if etree.QName(el).localname == "bookmarkStart":
                joy.setdefault(el.get(WQ + "name"), int(uid))
    return joy


def mundarija(matn, meta):
    """[(matn, anchor)] - mundarija qatorlari (ichki havolali, ketma-ket qatorlar)."""
    yozuvlar = []
    for uid, mt in meta["birliklar"].items():
        if len(mt["havolalar"]) == 1:
            a = anchor_of(mt["havolalar"][0])
            if a:
                yozuvlar.append((int(uid), " ".join(toza(matn[uid]).split()), a))
    # eng uzun ketma-ket blok
    blok, eng = [], []
    for y in yozuvlar:
        if blok and y[0] != blok[-1][0] + 1:
            blok = []
        blok.append(y)
        if len(blok) > len(eng):
            eng = list(blok)
    return eng if len(eng) >= 3 else []


def main():
    matn = yukla(ISH / "matn.json")
    meta = yukla(ISH / "meta.json")
    n = len(matn)
    joy = bookmark_joylari(meta)
    mund = mundarija(matn, meta)
    boshlar = []  # (boshlanish_uid, nom)
    yoq = []
    if mund:
        kutilayotgan = None  # Division/Section boshlanishi
        for uid, nom, a in mund:
            u = joy.get(a)
            if u is None:
                yoq.append(nom)
                continue
            if YUQORI.match(nom):
                if kutilayotgan is None:
                    kutilayotgan = u
                continue
            bosh = kutilayotgan if kutilayotgan is not None else u
            kutilayotgan = None
            boshlar.append((bosh, nom))
        mund_oxiri = mund[-1][0]
    else:
        mund_oxiri = 0
        for uid in range(1, n + 1):
            mt = meta["birliklar"][str(uid)]
            t = " ".join(toza(matn[str(uid)]).split())
            if not t:
                continue
            us = mt["uslub"].lower()
            sarl = us in ("heading1", "heading2", "title") or (
                BOB_NAQSH.match(t) and len(t) < 120 and not t.endswith("."))
            if sarl and (mt["sahifa_uzilishi"] or us.startswith("heading") or us == "title"):
                boshlar.append((uid, t))
    boshlar.sort()
    boblar = []
    if not boshlar or boshlar[0][0] > 1:
        boshlar.insert(0, (1, "0-qism (nom varag'i, ruxsatnoma, mundarija)"))
        raqam0 = 0
    else:
        raqam0 = 1
    for i, (b, nom) in enumerate(boshlar):
        t = boshlar[i + 1][0] - 1 if i + 1 < len(boshlar) else n
        boblar.append({"raqam": raqam0 + i, "nom": nom, "boshlanish": b, "tugash": t,
                       "birlik_soni": t - b + 1})
    saqla(ISH / "boblar.json", boblar)
    saqla(ISH / "bolish_info.json", {"mundarija": [m[1] for m in mund], "mundarija_oxiri": mund_oxiri,
                                     "faylda_yoq": yoq})
    print("Boblar: %d (0-qism bilan). Mundarijada bor, faylda yo'q: %d" % (len(boblar), len(yoq)))
    for b in boblar:
        print("  %2d  %4d-%4d  %s" % (b["raqam"], b["boshlanish"], b["tugash"], b["nom"]))


if __name__ == "__main__":
    main()
