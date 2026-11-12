"""Boblarga bo'lish to'g'riligini mexanik tekshiradi (CLAUDE.md 4.3).

Ishlatish: python Ish/bolish_tekshir.py
Faqat XATO va TEKSHIRING qatorlarini chiqaradi. Natija Ish/bolish_natija.txt ga ham yoziladi.
"""
import re
import statistics

from umumiy import ISH, toza, yukla

TUGATUVCHI = re.compile(r"[.!?…:;)\]»”\"'’]\s*$")
YUQORI = re.compile(r"^\s*(division|section)\s+\w+", re.I)


def main():
    matn = yukla(ISH / "matn.json")
    meta = yukla(ISH / "meta.json")
    boblar = yukla(ISH / "boblar.json")
    info = yukla(ISH / "bolish_info.json") if (ISH / "bolish_info.json").exists() else {}
    n = len(matn)
    xato, tek = [], []

    # uzluksiz qamrov
    kutilgan = 1
    for b in boblar:
        if b["boshlanish"] != kutilgan:
            xato.append("XATO: %d-bob %d dan boshlanadi, %d kutilgan (bo'shliq yoki takror)"
                        % (b["raqam"], b["boshlanish"], kutilgan))
        if b["tugash"] < b["boshlanish"]:
            xato.append("XATO: %d-bob oralig'i noto'g'ri" % b["raqam"])
        if b["birlik_soni"] != b["tugash"] - b["boshlanish"] + 1:
            xato.append("XATO: %d-bob birlik_soni noto'g'ri" % b["raqam"])
        kutilgan = b["tugash"] + 1
    if kutilgan != n + 1:
        xato.append("XATO: boblar %d da tugaydi, birliklar soni %d" % (kutilgan - 1, n))
    if sum(b["birlik_soni"] for b in boblar) != n:
        xato.append("XATO: boblardagi birliklar yig'indisi asl soniga teng emas")

    # raqamlar ketma-ket
    raq = [b["raqam"] for b in boblar]
    if raq != list(range(raq[0], raq[0] + len(raq))):
        xato.append("XATO: bob raqamlari ketma-ket emas: %s" % raq)

    def birinchi_matn(b):
        for u in range(b["boshlanish"], b["tugash"] + 1):
            t = " ".join(toza(matn[str(u)]).split())
            if t:
                return u, t
        return None, ""

    def oxirgi_matn(b):
        for u in range(b["tugash"], b["boshlanish"] - 1, -1):
            t = " ".join(toza(matn[str(u)]).split())
            if t:
                return u, t
        return None, ""

    mund = info.get("mundarija", [])
    for i, b in enumerate(boblar):
        u, t = birinchi_matn(b)
        if b["raqam"] != 0 or i > 0:
            nom = " ".join(b["nom"].split())
            nom_bosh = re.split(r"[:\s]", nom)[0].lower()
            if not (t.lower().startswith(nom_bosh) or YUQORI.match(t)):
                xato.append("XATO: %d-bob sarlavha bilan boshlanmaydi (birlik %s: %.60s)" % (b["raqam"], u, t))
            if mund and b["nom"] not in mund:
                xato.append("XATO: %d-bob nomi mundarijada yo'q: %s" % (b["raqam"], b["nom"]))
        if i + 1 < len(boblar):
            u2, t2 = oxirgi_matn(b)
            if b["raqam"] != 0 and not b.get("oxiri_tekshirildi") and not TUGATUVCHI.search(t2):
                tek.append("TEKSHIRING: %d-bob oxiri (birlik %s) jumla tugatuvchi belgisiz: …%.60s"
                           % (b["raqam"], u2, t2[-60:]))
        if b["birlik_soni"] < 3:
            tek.append("TEKSHIRING: %d-bob juda qisqa (%d birlik)" % (b["raqam"], b["birlik_soni"]))
    asosiy = [b["birlik_soni"] for b in boblar if b["raqam"] != 0]
    if asosiy:
        o = statistics.mean(asosiy)
        for b in boblar:
            if b["raqam"] != 0 and b["birlik_soni"] > 5 * o:
                tek.append("TEKSHIRING: %d-bob o'rtachadan 5 baravar uzun (%d birlik)" % (b["raqam"], b["birlik_soni"]))

    # mundarija bilan moslik: fayldagi boblar mundarija tartibida
    if mund:
        bob_nomlari = [b["nom"] for b in boblar if b["raqam"] != 0]
        mund_boblar = [m for m in mund if not YUQORI.match(m)]
        if bob_nomlari != mund_boblar[:len(bob_nomlari)]:
            xato.append("XATO: boblar tartibi mundarija bilan mos emas")

    # izoh yorliqlari chegarada uzilmagan
    for b in boblar[1:]:
        t = toza(matn[str(b["boshlanish"])])
        if re.match(r"^\s*(Izoh|Note)\s*\d+\s*:", t):
            xato.append("XATO: %d-bob izoh yorlig'i bilan boshlanadi (izoh uzilgan)" % b["raqam"])

    qatorlar = xato + tek
    eslatma = []
    if info.get("faylda_yoq"):
        eslatma.append("Eslatma: mundarijadagi %d ta yozuv bu faylda yo'q (fayl kitobning bir qismi): %s ..."
                       % (len(info["faylda_yoq"]), info["faylda_yoq"][0]))
    natija = "\n".join(qatorlar) if qatorlar else "XATO 0, TEKSHIRING 0"
    (ISH / "bolish_natija.txt").write_text(natija + ("\n" + "\n".join(eslatma) if eslatma else "") + "\n",
                                          encoding="utf-8")
    print(natija)
    for e in eslatma:
        print(e)


if __name__ == "__main__":
    main()
