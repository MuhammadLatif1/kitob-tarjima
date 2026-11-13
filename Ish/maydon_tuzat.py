"""joyla.py dan keyin: bir necha xatboshiga cho'zilgan maydonlarni (masalan, TOC) asl bilan moslaydi.

Ishlatish: python Ish/maydon_tuzat.py Asl/<nom>.docx Tarjima/<nom>_uz.docx
- tarjimada ortiqcha qo'shilgan fldChar end ni olib tashlaydi, yo'qolganini qaytaradi;
- asl xatboshidagi ichki giperhavola (w:hyperlink) tushib qolgan bo'lsa, maydon natijasi runlarini unga o'raydi.
"""
import copy
import shutil
import sys
import tempfile
import zipfile

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def fld(p):
    return [c.get(W + "fldCharType") for c in p.iter(W + "fldChar")]


def end_run():
    r = etree.Element(W + "r")
    f = etree.SubElement(r, W + "fldChar")
    f.set(W + "fldCharType", "end")
    return r


def main():
    asl, uz = sys.argv[1], sys.argv[2]
    ra = etree.fromstring(zipfile.ZipFile(asl).read("word/document.xml"))
    zu = zipfile.ZipFile(uz)
    ru = etree.fromstring(zu.read("word/document.xml"))
    pa, pu = list(ra.iter(W + "p")), list(ru.iter(W + "p"))
    if len(pa) != len(pu):
        sys.exit("XATO: xatboshilar soni farq qiladi")
    n = 0
    for i, (a, u) in enumerate(zip(pa, pu)):
        fa, fu = fld(a), fld(u)
        if fa != fu:
            if fu == fa + ["end"]:
                ends = [c for c in u.iter(W + "fldChar") if c.get(W + "fldCharType") == "end"]
                r = ends[-1].getparent()
                r.getparent().remove(r)
            elif fa == fu + ["end"] and fa[-1] == "end":
                u.append(end_run())
            else:
                print("TEKSHIRING %d: maydon tuzilishi farqli %s / %s" % (i + 1, fa, fu))
                continue
            n += 1
        ha = a.findall(W + "hyperlink")
        if len(ha) == 1 and not u.findall(".//" + W + "hyperlink"):
            sep = [c for c in u.iter(W + "fldChar") if c.get(W + "fldCharType") == "separate"]
            start = sep[-1].getparent() if sep else None
            runs = [c for c in u if c.tag == W + "r" and c.find(W + "t") is not None]
            if start is not None:
                runs = [c for c in runs if u.index(c) > u.index(start)]
            runs = [c for c in runs if c.find(W + "fldChar") is None]
            if runs:
                h = etree.Element(W + "hyperlink")
                for k, v in ha[0].attrib.items():
                    h.set(k, v)
                u.insert(u.index(runs[0]), h)
                for r in runs:
                    h.append(r)
                n += 1
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in zu.infolist():
            data = zu.read(item.filename)
            if item.filename == "word/document.xml":
                data = etree.tostring(ru, xml_declaration=True, encoding="UTF-8", standalone=True)
            out.writestr(item, data)
    zu.close()
    shutil.move(tmp, uz)
    print("Maydon tuzatishlari: %d" % n)


if __name__ == "__main__":
    main()
