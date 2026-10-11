"""Convert the cleaned Project Gutenberg Dublin Core CSV into a MARC21 file for Koha.
Usage: python csv_to_marc.py gutenberg-clean-500.csv gutenberg-500.mrc
"""
import csv, re, sys, datetime
from pymarc import Record, Field, Subfield, Indicators

LANG = {"en":"eng","fr":"fre","fi":"fin","nl":"dut","pt":"por","de":"ger","es":"spa","it":"ita",
        "eo":"epo","hu":"hun","el":"gre","tl":"tgl","ca":"cat","la":"lat","sv":"swe","no":"nor"}
ITEMTYPE = {"Text":"BK","Sound":"CF"}          # Koha sample-data item types (942 $c)
FORM_TERMS = {"Fiction","Juvenile fiction","Poetry","Biography","Periodicals","Pictorial works",
              "Sketch-books","Drama","Juvenile poetry","Juvenile drama","Humor","Correspondence",
              "Sources","Bibliography","Dictionaries","Maps","Diaries","Anecdotes"}
PERIOD = re.compile(r"^(\d{1,2}(st|nd|rd|th) century|\d{3,4}(-\d{0,4})?)$")
ARTICLES = {"en":("a ","an ","the ")}
DATES = re.compile(r"^(.*?),?\s+(\d{3,4}\??-(?:\d{3,4}\??)?|\d{1,2}th century.*)$")
today = datetime.date.today().strftime("%y%m%d")

def name_fields(person):
    """'Meade, L. T., 1854-1914' -> ($a 'Meade, L. T.,', $d '1854-1914')"""
    m = DATES.match(person)
    if m: return m.group(1).strip().rstrip(",") + ",", m.group(2)
    return person, None

def sf(code, val): return Subfield(code=code, value=val)

def person_field(tag, person, relator=None):
    a, d = name_fields(person)
    subs = [sf("a", a)]
    if d: subs.append(sf("d", d if not relator else d + ","))
    elif relator: subs[0] = sf("a", a + ",")
    if relator: subs.append(sf("e", relator + "."))
    elif d is None and not a.endswith("."): pass
    return Field(tag=tag, indicators=Indicators("1"," "), subfields=subs)

def end_punct(s): return s if s[-1] in ".?!" else s + "."

def build(row):
    rec = Record(force_utf8=True)
    typ = row["dc.type"]
    rec.leader = rec.leader[:6] + ("i" if typ == "Sound" else "a") + "m" + rec.leader[8:]
    rec.add_field(Field(tag="001", data="PG" + row["dc.identifier"]))
    langs = [LANG.get(l, "und") for l in row["dc.language"].split("||") if l]
    lang0 = langs[0] if langs else "und"
    if typ == "Sound":   # music/sound 008 layout
        body = "nn" + "n" + "n" + "#" + "o" + "######" + "##" + "#" + "n" + "#"
    else:                # books 008 layout, form of item = online
        body = "####" + "#" + "o" + "####" + "#" + "0" + "0" + "0" + "#" + "u" + "#"
    f008 = today + "n" + "uuuu" + "uuuu" + "xx#" + body + lang0 + "#" + "d"
    f008 = f008.replace("#", " ")   # blank positions are spaces in MARC
    assert len(f008) == 40, len(f008)
    rec.add_field(Field(tag="008", data=f008))
    if len(langs) > 1 or lang0 != "eng":
        rec.add_field(Field(tag="041", indicators=Indicators("0"," "), subfields=[sf("a", l) for l in langs]))
    rec.add_field(Field(tag="040", indicators=Indicators(" "," "), subfields=[sf("b","eng"), sf("c","GZU")]))

    creators = [c for c in row["dc.creator"].split("||") if c and c not in ("Anonymous","Various")]
    if creators: rec.add_field(person_field("100", creators[0]))

    title = row["dc.title"].strip()
    ind1 = "1" if creators else "0"
    nf = 0
    if row["dc.language"].split("||")[0] == "en":
        for art in ARTICLES["en"]:
            if title.lower().startswith(art): nf = len(art); break
    if ": " in title:
        a, b = title.split(": ", 1)
        subs = [sf("a", a + " :"), sf("b", end_punct(b))]
    else:
        subs = [sf("a", end_punct(title))]
    rec.add_field(Field(tag="245", indicators=Indicators(ind1, str(nf)), subfields=subs))

    rec.add_field(Field(tag="336", indicators=Indicators(" "," "), subfields=
        [sf("a","spoken word"),sf("b","spw"),sf("2","rdacontent")] if typ=="Sound" else
        [sf("a","text"),sf("b","txt"),sf("2","rdacontent")]))
    rec.add_field(Field(tag="337", indicators=Indicators(" "," "), subfields=[sf("a","computer"),sf("b","c"),sf("2","rdamedia")]))
    rec.add_field(Field(tag="338", indicators=Indicators(" "," "), subfields=[sf("a","online resource"),sf("b","cr"),sf("2","rdacarrier")]))
    rec.add_field(Field(tag="500", indicators=Indicators(" "," "), subfields=[sf("a", f"Project Gutenberg release date: {row['dcterms.issued']}.")]))

    for s in [x for x in row["dc.subject"].split("||") if x]:
        parts = [p.strip() for p in s.split(" -- ")]
        subs = [sf("a", parts[0])]
        for p in parts[1:]:
            code = "v" if p in FORM_TERMS else "y" if PERIOD.match(p) else "x"
            subs.append(sf(code, p))
        rec.add_field(Field(tag="650", indicators=Indicators(" ","0"), subfields=subs))

    for c in creators[1:]:                       # extra creators become 700 added entries
        rec.add_field(person_field("700", c))
    for c in [x for x in row["dc.contributor"].split("||") if x]:
        m = re.match(r"^(.*?)\s*\[(.+?)\]$", c)
        person, role = (m.group(1), m.group(2).lower()) if m else (c, None)
        person = re.sub(r"\s*\((illustrator|editor|translator|compiler)\)\s*$", "", person, flags=re.I)
        rec.add_field(person_field("700", person, role))

    rec.add_field(Field(tag="856", indicators=Indicators("4","0"), subfields=[
        sf("u", f"https://www.gutenberg.org/ebooks/{row['dc.identifier']}"), sf("y","Read online at Project Gutenberg")]))
    rec.add_field(Field(tag="942", indicators=Indicators(" "," "), subfields=[sf("c", ITEMTYPE.get(typ,"BK"))]))
    return rec

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    n = 0
    with open(src, encoding="utf-8", newline="") as f, open(dst, "wb") as out:
        for row in csv.DictReader(f):
            out.write(build(row).as_marc()); n += 1
    print(f"wrote {n} records to {dst}")
