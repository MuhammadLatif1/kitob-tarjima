"""Yakuniy mexanik sifat tekshiruvi (CLAUDE.md 7) va hisobot qoralamasi.

Ishlatish: python Ish/tekshir.py <asl_nom> [--qamrov BOSH-OXIR]
  <asl_nom>: Asl/<asl_nom>.docx va Tarjima/<asl_nom>_uz.docx
  --qamrov: faqat shu birliklar oralig'ining tarjimasi talab qilinadi (qisman tarjima uchun).
Natija: Ish/tekshir_natija.txt (hisobotning 1, 6, 7-bo'limlari qoralamasi).
"""
import hashlib
import re
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

from lxml import etree

from umumiy import BELGI, ISH, LOYIHA, MATNLI_QISMLAR, WQ, raqamlar, tarjima_kerak, toza, yukla

INGLIZ = set("the and of to is are was were that this with for from which have has be by it as you your "
             "can will not or but they their there what when how".split())


def sanoq(z):
    c = Counter()
    for n in z.namelist():
        if not MATNLI_QISMLAR.match(n):
            continue
        root = etree.fromstring(z.read(n))
        c["xatboshi"] += sum(1 for _ in root.iter(WQ + "p"))
        c["jadval"] += sum(1 for _ in root.iter(WQ + "tbl"))
        c["rasm"] += sum(1 for _ in root.iter(WQ + "drawing"))
        c["izoh_havolasi"] += sum(1 for _ in root.iter(WQ + "footnoteReference", WQ + "endnoteReference"))
        if n.endswith(("footnotes.xml", "endnotes.xml")):
            c["izoh"] += sum(1 for e in root if etree.QName(e).localname in ("footnote", "endnote")
                             and e.get(WQ + "type") is None)
    return c


def media(z):
    return {n: hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith("word/media/")}


def inglizcha(s):
    sozlar = re.findall(r"[A-Za-z‘’ʻʼ'-]+", s.lower())
    if len(sozlar) < 6:
        return False
    return sum(w in INGLIZ for w in sozlar) / len(sozlar) > 0.2


def lugat_tasdiqlangan():
    p = LOYIHA / "Lugat.txt"
    if not p.exists():
        return []
    bolim, natija = None, []
    for q in p.read_text(encoding="utf-8").splitlines():
        s = q.strip()
        if s in ("TASDIQLANGAN", "TAKLIF", "MUQOBIL VARIANTLAR"):
            bolim = s
        elif bolim == "TASDIQLANGAN" and "→" in s:
            en, rest = s.split("→", 1)
            if "ko‘p ma’noli" in rest:
                continue  # kontekstga bog'liq so'z: mexanik tekshirilmaydi
            natija.append((en.strip(), rest.split("|")[0].strip()))
    return natija


# Ko'p ma'noli umumiy so'zlar: atama sifatida faqat shu kontekstda tekshiriladi
ATAMA_KONTEKST = {
    "order": r"\b(the|an?|each|same|new)\s+order\b(?!\s+(to|of|in)\b)|\border\s+[A-Z]",
    "division": r"\bDivision\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)\b",
    "section": r"\bSection\s+(One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven)\b",
    "chapter": r"\bChapter\s+\d+",
    "domain": r"\b(three|the)\s+domains?\b(?!\s+of\s+(the\s+)?protein)",
    "replicate": r"\bviruse?s?\b.*\breplicat",
}


def atama_bor(en, matn):
    k = ATAMA_KONTEKST.get(en.lower())
    if k:
        return re.search(k, matn) is not None
    flag = 0 if en[:1].isupper() and " " not in en else re.I
    return re.search(r"\b%s\b" % re.escape(en), matn, flag) is not None


def sahifalar(docx):
    try:
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", d, str(docx)],
                           capture_output=True, timeout=600)
            pdf = Path(d) / (Path(docx).stem + ".pdf")
            if not pdf.exists():
                return None
            data = pdf.read_bytes()
            m = re.findall(rb"/Type\s*/Pages\b[^>]*?/Count\s+(\d+)", data)
            return max(int(x) for x in m) if m else None
    except Exception:
        return None


def main():
    if len(sys.argv) < 2:
        sys.exit("Ishlatish: python Ish/tekshir.py <asl_nom> [--qamrov BOSH-OXIR]")
    nom = sys.argv[1]
    qamrov = None
    if "--qamrov" in sys.argv:
        a, b = sys.argv[sys.argv.index("--qamrov") + 1].split("-")
        qamrov = (int(a), int(b))
    asl = LOYIHA / "Asl" / (nom + ".docx")
    uz = LOYIHA / "Tarjima" / (nom + "_uz.docx")
    xato, eslatma = [], []
    za, zu = zipfile.ZipFile(asl), zipfile.ZipFile(uz)

    sa, su = sanoq(za), sanoq(zu)
    for k in ("xatboshi", "jadval", "izoh", "rasm", "izoh_havolasi"):
        if sa[k] != su[k]:
            xato.append("XATO: %s soni farq qiladi: asl %d, tarjima %d" % (k, sa[k], su[k]))
    ma, mu = media(za), media(zu)
    if ma != mu:
        for n in sorted(set(ma) | set(mu)):
            if ma.get(n) != mu.get(n):
                xato.append("XATO: rasm fayli farq qiladi: %s" % n)

    # izoh havolalari tartibi
    def izoh_idlar(z):
        ids = []
        for n in z.namelist():
            if MATNLI_QISMLAR.match(n):
                root = etree.fromstring(z.read(n))
                ids += [e.get(WQ + "id") for e in root.iter(WQ + "footnoteReference", WQ + "endnoteReference")]
        return ids
    if izoh_idlar(za) != izoh_idlar(zu):
        xato.append("XATO: izoh havolalari tartibi yoki raqamlari o'zgargan")

    matn = yukla(ISH / "matn.json")
    tarj = yukla(ISH / "tarjima.json") if (ISH / "tarjima.json").exists() else {}
    kerak = [u for u in matn if tarjima_kerak(matn[u]) and (qamrov is None or qamrov[0] <= int(u) <= qamrov[1])]
    yoq = [u for u in kerak if u not in tarj]
    if yoq:
        xato.append("XATO: tarjimasiz birliklar: %d ta (birinchisi %s)" % (len(yoq), yoq[0]))

    # tarjima qilingan fayldan matnni qayta ajratib, birliklar bo'yicha tekshirish
    uz_matn = {}
    uid = 0
    for n in sorted([n for n in zu.namelist() if MATNLI_QISMLAR.match(n)],
                    key=lambda n: (n != "word/document.xml", n)):
        for p in etree.fromstring(zu.read(n)).iter(WQ + "p"):
            uid += 1
            uz_matn[str(uid)] = "".join(t.text or "" for t in p.iter(WQ + "t"))
    tasdiq = lugat_tasdiqlangan()
    for u in kerak:
        if u not in tarj:
            continue
        t = uz_matn.get(u, "")
        if BELGI.search(t) or "⟦" in t or "⟧" in t:
            xato.append("XATO %s: ⟦...⟧ belgisi matnda qolgan" % u)
        if inglizcha(t):
            xato.append("XATO %s: inglizcha qolgan: %.60s" % (u, t))
        if Counter(raqamlar(matn[u])) != Counter(raqamlar(tarj[u])):
            ra, rt = Counter(raqamlar(matn[u])), Counter(raqamlar(tarj[u]))
            xato.append("XATO %s: raqamlar farq qiladi: yo'q %s, ortiqcha %s"
                        % (u, sorted((ra - rt).elements()), sorted((rt - ra).elements())))
        if re.search(r"[“”\"]", t):
            xato.append("XATO %s: iqtibos «...» ichida emas" % u)
        for en, uzt in tasdiq:
            if atama_bor(en, toza(matn[u])):
                soz = uzt.strip("«»\"' ").split()[0].strip("«»").lower()
                soz = re.sub(r"(lar|moq|mak|gan)$", "", soz)
                ildiz = soz[: max(4, len(soz) - 1)]
                if ildiz not in t.lower() and en.lower() not in t.lower():
                    xato.append("XATO %s: TASDIQLANGAN atama «%s → %s» ishlatilmagan" % (u, en, uzt))
    try:
        import docx
        docx.Document(str(uz))
    except Exception as e:
        xato.append("XATO: fayl python-docx bilan ochilmadi: %s" % e)
    pa, pu = sahifalar(asl), sahifalar(uz)
    if pa and pu:
        eslatma.append("Sahifalar soni (LibreOffice PDF): asl %d, tarjima %d" % (pa, pu))
    else:
        eslatma.append("Sahifalar soni: LibreOffice bilan aniqlab bo'lmadi")

    rasmlar = sorted(ma, key=lambda n: int(re.sub(r"\D", "", n) or 0))
    natija = []
    natija.append("1) QAMROV")
    natija.append("   Xatboshi: %d, jadval: %d, sahifa osti izohi: %d, rasm: %d (asl bilan solishtirilgan)"
                  % (su["xatboshi"], su["jadval"], su["izoh"], su["rasm"]))
    natija.append("   Tarjima qilingan birliklar: %d / %d%s" % (len([u for u in kerak if u in tarj]), len(kerak),
                  " (qamrov: %d-%d)" % qamrov if qamrov else ""))
    natija.append("6) RASMLAR VA QO'LDA TEKSHIRISH")
    natija.append("   word/media/ dagi %d ta rasm o'zgarishsiz qoldi. Rasm ichidagi yozuvlar tarjima qilinmadi." % len(rasmlar))
    natija.append("   Rasmlar: " + ", ".join(Path(r).name for r in rasmlar))
    natija.append("   Qo'lda: mundarija havolalari ishlashini Word da tekshiring; sahifa raqamlari maydon bo'lsa F9 bilan yangilang.")
    natija.append("7) SIFAT TEKSHIRUVI")
    natija += ["   " + q for q in (xato or ["XATO 0"])]
    natija += ["   " + q for q in eslatma]
    (ISH / "tekshir_natija.txt").write_text("\n".join(natija) + "\n", encoding="utf-8")
    for q in xato:
        print(q)
    for q in eslatma:
        print(q)
    print("XATO %d" % len(xato))
    sys.exit(1 if xato else 0)


if __name__ == "__main__":
    main()
