"""Bob tarjima faylini Ish/matn.json bilan solishtiradi (belgilar, qo'shtirnoq, raqamlar).

Ishlatish: python Ish/bolak_tekshir.py Ish/boblar/bob_NN.json
Chiqish: XATO va OGOHLANTIRISH qatorlari; oxirida holat qatori.
"""
import re
import sys
from collections import Counter
from pathlib import Path

from umumiy import ISH, KIRILL, belgilar, qoshtirnoq, raqamlar, tarjima_kerak, toza, yukla

def muvozanat(s):
    stack = []
    for b in belgilar(s):
        m = re.match(r"⟦(/?)([sh])(\d+)⟧", b)
        if not m:
            continue
        yop, tur, n = m.groups()
        if not yop:
            stack.append(tur + n)
        else:
            if not stack or stack[-1] != tur + n:
                return False
            stack.pop()
    return not stack


def tekshir(bob_fayl, matn):
    tarj = yukla(bob_fayl)
    xato, ogoh = [], []
    for uid, t in tarj.items():
        if uid not in matn:
            xato.append("XATO %s: bunday birlik yo'q" % uid)
            continue
        a = matn[uid]
        if tarjima_kerak(a) and not toza(t).strip():
            xato.append("XATO %s: tarjima bo'sh" % uid)
        if Counter(belgilar(a)) != Counter(belgilar(t)):
            xato.append("XATO %s: belgilar mos emas: asl %s, tarjima %s" % (uid, belgilar(a), belgilar(t)))
        elif not muvozanat(t):
            xato.append("XATO %s: belgilar tartibi buzilgan (ochilish/yopilish)" % uid)
        och, yop = qoshtirnoq()
        notogri = re.sub("[%s%s]" % (och, yop), "", "«»“”\"„")
        if re.search("[%s]" % re.escape(notogri), toza(t)):
            xato.append("XATO %s: boshqa turdagi qo'shtirnoq qolgan, %s...%s ishlating" % (uid, och, yop))
        if toza(t).count(och) != toza(t).count(yop):
            ogoh.append("OGOHLANTIRISH %s: %s va %s soni teng emas" % (uid, och, yop))
        if KIRILL.search(toza(t)):
            xato.append("XATO %s: tarjimada kirill harflari qolgan" % uid)
        ra, rt = Counter(raqamlar(a)), Counter(raqamlar(t))
        if ra - rt:
            ogoh.append("OGOHLANTIRISH %s: raqamlar yo'qolgan: %s" % (uid, sorted((ra - rt).elements())))
        if rt - ra:
            ogoh.append("OGOHLANTIRISH %s: ortiqcha raqamlar: %s" % (uid, sorted((rt - ra).elements())))
    # bob oralig'i bo'yicha qamrov
    m = re.search(r"bob_(\d+)\.json$", str(bob_fayl))
    tayyor = ""
    if m and (ISH / "boblar.json").exists():
        r = int(m.group(1))
        for b in yukla(ISH / "boblar.json"):
            if b["raqam"] == r:
                kerak = [str(u) for u in range(b["boshlanish"], b["tugash"] + 1) if tarjima_kerak(matn[str(u)])]
                bor = [u for u in kerak if u in tarj]
                tashqari = [u for u in tarj if not b["boshlanish"] <= int(u) <= b["tugash"]]
                for u in tashqari:
                    xato.append("XATO %s: birlik bu bob oralig'ida emas" % u)
                tayyor = "Tayyor: %d/%d birlik" % (len(bor), len(kerak))
                if len(bor) < len(kerak):
                    qolgan = [u for u in kerak if u not in tarj]
                    tayyor += " (qolgan birinchi: %s)" % qolgan[0]
    return xato, ogoh, tayyor


def main():
    if len(sys.argv) != 2:
        sys.exit("Ishlatish: python Ish/bolak_tekshir.py Ish/boblar/bob_NN.json")
    matn = yukla(ISH / "matn.json")
    xato, ogoh, tayyor = tekshir(Path(sys.argv[1]), matn)
    for q in xato + ogoh:
        print(q)
    print("XATO %d, OGOHLANTIRISH %d. %s" % (len(xato), len(ogoh), tayyor))
    sys.exit(1 if xato else 0)


if __name__ == "__main__":
    main()
