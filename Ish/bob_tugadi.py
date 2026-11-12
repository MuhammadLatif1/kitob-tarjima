"""Bob tarjimasi tugagach: tekshiradi, yangi atamalarni atamalar_joriy.json ga qo'shadi,
holat.txt ni yangilaydi, birlashtirib nusxaga joylaydi.

Ishlatish: python Ish/bob_tugadi.py NN
"""
import subprocess
import sys

from umumiy import ISH, LOYIHA, saqla, yukla


def main():
    r = int(sys.argv[1])
    bf = ISH / "boblar" / ("bob_%02d.json" % r)
    p = subprocess.run([sys.executable, str(ISH / "bolak_tekshir.py"), str(bf)], capture_output=True, text=True)
    print(p.stdout.strip().splitlines()[-1])
    if p.returncode != 0:
        print(p.stdout)
        sys.exit("Bob tekshiruvidan o'tmadi")
    if "qolgan birinchi" in p.stdout:
        sys.exit("Bob to'liq emas")
    ef = ISH / "boblar" / ("bob_%02d_eslatma.json" % r)
    esl = yukla(ef) if ef.exists() else {}
    at = yukla(ISH / "atamalar_joriy.json")
    n = 0
    for x in esl.get("yangi_atamalar", []):
        en = (x.get("en") or "").strip()
        if not en or en.lower() in {k.lower() for k in at}:
            continue
        at[en] = {"uz": x.get("uz", ""), "izoh": x.get("izoh", ""), "joy": x.get("joy", ""),
                  "holat": x.get("holat", "TASDIQLANGAN")}
        n += 1
    saqla(ISH / "atamalar_joriy.json", at)
    boblar = yukla(ISH / "boblar.json")
    tugagan = sorted(int(f.stem.split("_")[1]) for f in (ISH / "boblar").glob("bob_??.json"))
    keyingi = next((b for b in boblar if b["raqam"] not in tugagan and not b.get("tarjima_qilinmaydi")), None)
    hp = ISH / "holat.txt"
    qatorlar = [q for q in hp.read_text(encoding="utf-8").splitlines()
                if not q.startswith(("Tugagan boblar:", "Keyingi:"))]
    qatorlar.insert(2, "Tugagan boblar: " + ", ".join(str(t) for t in tugagan))
    qatorlar.insert(3, "Keyingi: " + ("%d-raqamli bob (%s), birlik %d dan" % (keyingi["raqam"], keyingi["nom"], keyingi["boshlanish"])
                                      if keyingi else "hamma boblar tayyor; tekshir.py va yakun.py qoldi"))
    hp.write_text("\n".join(qatorlar) + "\n", encoding="utf-8")
    for s in ("birlashtir.py", "joyla.py"):
        args = [sys.executable, str(ISH / s)]
        if s == "joyla.py":
            args.append(str(LOYIHA / "Tarjima" / (yukla(ISH / "meta.json")["fayl"].split("/")[-1][:-5] + "_uz.docx")))
        out = subprocess.run(args, capture_output=True, text=True)
        print(out.stdout.strip())
        if out.returncode != 0:
            print(out.stderr)
            sys.exit(s + " xato")
    print("Yangi atamalar: %d. Keyingi: %s" % (n, keyingi["nom"] if keyingi else "yo'q"))


if __name__ == "__main__":
    main()
