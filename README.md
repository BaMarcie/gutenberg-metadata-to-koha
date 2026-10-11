# From Project Gutenberg metadata to a Koha catalogue

A small, reproducible metadata-migration project: clean 500 Project Gutenberg catalogue records in OpenRefine, map them to Dublin Core, convert them to MARC21 with Python, and bulk-import them into a Koha 25.11 test instance.

**Result:** 500 records in, 500 records imported into Koha, 0 rejected or ignored.

## Why this project
Library data rarely arrives ready to load. This project walks the whole path a real migration takes: inspect, clean, map, convert, load, verify. It is a small-scale rehearsal of the same steps used when moving records between systems.

## Pipeline

| Step | Tool | What happened |
|---|---|---|
| 1. Clean | OpenRefine 3.10 (GREL) | Normalised titles; split the combined `Authors` field into creator and contributor; kept role labels such as `[Illustrator]`; joined subjects and languages with `\|\|`; renamed columns to Dublin Core |
| 2. Record the steps | OpenRefine history | Exported the operation history as JSON (`docs/openrefine-history.json`) so the cleaning can be replayed on another batch |
| 3. Convert | Python 3 + pymarc | `scripts/csv_to_marc.py` builds a MARC21 file from the clean CSV |
| 4. Load | Koha 25.11 on Ubuntu 24.04 (VirtualBox) | Staged and imported with *Tools > Stage MARC records for import* |
| 5. Verify | Koha staff interface | Searched and inspected records, including the MARC view |

## Cataloguing rules applied
- The first `[Editor]` or `[Compiler]` becomes the main creator when a record has no author. Translators and illustrators never become the main creator.
- Everyone else with a bracketed role is a contributor and keeps the role label, which becomes the MARC relator term in 700 `$e`.
- Records with only a translator or illustrator have no 100 field; the title is the main entry.
- `Anonymous` and `Various` do not get a 100 field.
- A second or later creator becomes a 700 added entry.

## Field mapping

| Dublin Core (cleaned CSV) | MARC21 |
|---|---|
| `dc.identifier` | 001 (prefixed `PG`), 856 `$u` link |
| `dc.title` | 245 `$a` / `$b`, with non-filing characters for English articles |
| `dc.creator` | 100 (first), 700 (others) |
| `dc.contributor` | 700 with `$e` relator term |
| `dc.subject` | 650 `_0` with `$v` / `$y` / `$x` subdivisions |
| `dc.language` | 008/35-37 and 041 (ISO 639-2/B codes) |
| `dc.type` | Leader/06, 336, and Koha item type in 942 `$c` |
| `dcterms.issued` | 500 note (Project Gutenberg release date) |

## Repository contents
- `data/gutenberg-clean-500.csv` - cleaned Dublin Core data
- `data/gutenberg-500.mrc` - MARC21 file used for the Koha import
- `docs/openrefine-history.json` - replayable OpenRefine operation history
- `scripts/csv_to_marc.py` - CSV to MARC21 conversion

## Reproduce it
```bash
pip install pymarc
python scripts/csv_to_marc.py data/gutenberg-clean-500.csv data/gutenberg-500.mrc
```
To replay the cleaning, open a Project Gutenberg metadata sample in OpenRefine, choose *Undo / Redo > Apply...*, and paste `docs/openrefine-history.json`.

## Known limitations
- Subject subdivisions are coded by a simple rule (form terms to `$v`, periods to `$y`, everything else to `$x`), so some geographic subdivisions are coded as topical rather than `$z`.
- `Sound` records are assigned Koha item type `CF` because the sample item types have no spoken-audio type; adjust to your own item types.
- Records are catalogue-level only; no item (holdings) records were created.
- A few source values contain duplicated roles, for example `Smith, Harry L. (Illustrator) [Illustrator]`; the converter strips the duplicate.

## Data source
Bibliographic metadata comes from the Project Gutenberg catalogue (https://www.gutenberg.org). Project Gutenberg's catalogue data is freely available; see their site for terms.

## Author
Brighton Tizirai - Discovery and Metadata Librarian. linkedin.com/in/brightontizirai
