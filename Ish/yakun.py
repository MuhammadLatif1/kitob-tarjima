"""Yangi atamalarni Lugat.txt ga qo'shadi va Tarjima/<asl_nom>_hisobot.txt ni yig'adi.

Ishlatish: python Ish/yakun.py <asl_nom>
Manbalar: Ish/atamalar_joriy.json, Ish/boblar/bob_NN_eslatma.json, Ish/tekshir_natija.txt,
          Ish/boblar.json, Ish/bolish_natija.txt
"""
import re
import sys

from umumiy import ISH, LOYIHA, yukla

BOLIMLAR = ("TASDIQLANGAN", "TAKLIF", "MUQOBIL VARIANTLAR")


def lugat_oqi(p):
    bosh, bolim, b = [], None, {k: [] for k in BOLIMLAR}
    for q in p.read_text(encoding="utf-8").splitlines():
        if q.strip() in BOLIMLAR:
            bolim = q.strip()
        elif bolim is None:
            bosh.append(q)
        elif q.strip():
            b[bolim].append(q.strip())
    return bosh, b


def main():
    if len(sys.argv) != 2:
        sys.exit("Ishlatish: python Ish/yakun.py <asl_nom>")
    nom = sys.argv[1]
    lp = LOYIHA / "Lugat.txt"
    bosh, b = lugat_oqi(lp)
    mavjud = {q.split("→")[0].strip().lower() for k in BOLIMLAR for q in b[k] if "→" in q}
    joriy = yukla(ISH / "atamalar_joriy.json") if (ISH / "atamalar_joriy.json").exists() else {}
    yangi = []
    for en, v in joriy.items():
        if en.lower() in mavjud:
            continue
        q = "%s → %s | %s | %s" % (en, v["uz"], v.get("izoh", ""), v.get("joy", ""))
        b["MUQOBIL VARIANTLAR" if v.get("holat") == "MUQOBIL" else "TAKLIF"].append(q)
        yangi.append(q)
        mavjud.add(en.lower())
    bosh = [("Oxirgi yangilanish: %s" % nom) if q.startswith("Oxirgi yangilanish") else q for q in bosh]
    out = list(bosh)
    for k in BOLIMLAR:
        if out and out[-1].strip():
            out.append("")
        out.append(k)
        out += b[k]
    lp.write_text("\n".join(out) + "\n", encoding="utf-8")

    # hisobot
    boblar = yukla(ISH / "boblar.json")
    esl = {}
    for f in sorted((ISH / "boblar").glob("bob_*_eslatma.json")):
        r = int(re.search(r"bob_(\d+)_", f.name).group(1))
        esl[r] = yukla(f)
    tek = (ISH / "tekshir_natija.txt").read_text(encoding="utf-8").splitlines()
    bol = (ISH / "bolish_natija.txt").read_text(encoding="utf-8").strip()
    nomi = {x["raqam"]: x["nom"] for x in boblar}

    def bob_royxat(kalit):
        q = []
        for r, e in esl.items():
            for x in e.get(kalit, []):
                q.append("   [%s] %s" % (nomi.get(r, r), x if isinstance(x, str) else
                                          " | ".join("%s" % v for v in x.values())))
        return q or ["   Yo'q"]

    h = ["TARJIMA HISOBOTI: %s" % nom, ""]
    i7 = next((i for i, q in enumerate(tek) if q.startswith("6)")), len(tek))
    h += tek[:i7]
    h += ["2) NOANIQ JOYLAR"] + bob_royxat("noaniq")
    h += ["3) IQTIBOSLAR VA SAHIFA OSTI IZOHLARI"] + bob_royxat("iqtiboslar")
    h += ["4) LUG'ATGA QO'SHILGAN YANGI ATAMALAR"] + (["   " + q for q in yangi] or ["   Yo'q"])
    h += ["5) TASDIQ KERAK ATAMALAR"] + (["   " + q for q in b["TAKLIF"]] or ["   Yo'q"])
    h += tek[i7:]
    h += ["8) BOBLARGA BO'LISH"]
    h += ["   %2d. %s (birliklar %d-%d)" % (x["raqam"], x["nom"], x["boshlanish"], x["tugash"]) for x in boblar]
    h += ["   Bo'lish tekshiruvi: " + bol.replace("\n", "\n   ")]
    out = LOYIHA / "Tarjima" / (nom + "_hisobot.txt")
    out.write_text("\n".join(h) + "\n", encoding="utf-8")
    print("Lug'atga qo'shildi: %d. Hisobot: %s" % (len(yangi), out))


if __name__ == "__main__":
    main()
