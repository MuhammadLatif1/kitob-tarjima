"""Ish/boblar/bob_NN.json fayllarini bitta Ish/tarjima.json ga birlashtiradi (CLAUDE.md 4.6).

Ishlatish: python Ish/birlashtir.py
Id lar o'zgarmaydi, tartib asl bilan bir xil. Takror yoki chegara tashqarisidagi birlik XATO.
"""
import re
import sys
from collections import OrderedDict

from umumiy import ISH, saqla, tarjima_kerak, yukla


def main():
    matn = yukla(ISH / "matn.json")
    boblar = {b["raqam"]: b for b in yukla(ISH / "boblar.json")}
    jami = {}
    xato = []
    for f in sorted((ISH / "boblar").glob("bob_*.json")):
        m = re.match(r"bob_(\d+)\.json$", f.name)
        if not m:
            continue
        r = int(m.group(1))
        b = boblar.get(r)
        if b is None:
            xato.append("XATO: %s - bunday bob yo'q" % f.name)
            continue
        for uid, t in yukla(f).items():
            if not b["boshlanish"] <= int(uid) <= b["tugash"]:
                xato.append("XATO: %s dagi %s birlik bob oralig'ida emas" % (f.name, uid))
            elif uid in jami:
                xato.append("XATO: %s birlik ikki marta keldi" % uid)
            else:
                jami[uid] = t
    natija = OrderedDict((u, jami[u]) for u in matn if u in jami)
    saqla(ISH / "tarjima.json", natija)
    kerak = [u for u in matn if tarjima_kerak(matn[u])]
    yoq = [u for u in kerak if u not in natija]
    for q in xato:
        print(q)
    print("Birlashtirildi: %d birlik. Tarjima kerak: %d, tarjimasiz qolgan: %d" % (len(natija), len(kerak), len(yoq)))
    sys.exit(1 if xato else 0)


if __name__ == "__main__":
    main()
