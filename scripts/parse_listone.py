#!/usr/bin/env python3
"""Parse the public Fantacalcio.it 2026/27 quotations HTML into validated JSON."""
from __future__ import annotations
import json, re, sys
from html.parser import HTMLParser
from pathlib import Path

EXPECTED_SEASON = "2026/27"
ROLE_COUNTS = {"p": 76, "d": 216, "c": 206, "a": 105}
COL_KEYS = {"sq", "c_qi", "c_qa", "c_fvm", "m_qi", "m_qa", "m_fvm"}

class RowParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]; self.row=None; self.capture=None; self.buf=[]
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="tr" and "player-row" in a.get("class", "").split():
            self.row={"data_index":a.get("data-index"),"name":a.get("data-filter-keywords"),
                      "team_id":a.get("data-filter-team-id"),"role_classic":a.get("data-filter-role-classic"),
                      "role_mantra":a.get("data-filter-role-mantra"),"href":None,"values":{}}
        elif self.row is not None and tag=="a" and "player-link" in a.get("class", "").split():
            self.row["href"]=a.get("href")
        elif self.row is not None and tag=="td" and a.get("data-col-key"):
            self.capture=a["data-col-key"]; self.buf=[]
    def handle_data(self, data):
        if self.capture: self.buf.append(data)
    def handle_endtag(self, tag):
        if tag=="td" and self.capture:
            self.row["values"][self.capture]=" ".join("".join(self.buf).split())
            self.capture=None; self.buf=[]
        elif tag=="tr" and self.row is not None:
            self.rows.append(self.row); self.row=None

def main(src, dst):
    html=Path(src).read_text(encoding="utf-8", errors="replace")
    if "Quotazioni e FVM Fantacalcio Serie A 2026/27" not in html:
        raise SystemExit("ERRORE: pagina non corrisponde alla stagione 2026/27")
    parser=RowParser(); parser.feed(html); rows=parser.rows
    if len(rows)<500: raise SystemExit(f"ERRORE: solo {len(rows)} righe giocatore; import bloccato")
    counts={r:0 for r in ROLE_COUNTS}; ids=set(); out=[]
    for n,r in enumerate(rows):
        role=r["role_classic"]
        if role not in counts: raise SystemExit(f"ERRORE: ruolo Classic non valido alla riga {n}: {role}")
        counts[role]+=1
        if not all([r["name"],r["team_id"],r["href"]]):
            raise SystemExit(f"ERRORE: dati identificativi mancanti alla riga {n}")
        match=re.search(r"/(\d+)(?:/|\?.*)?$", r["href"])
        if not match: raise SystemExit(f"ERRORE: ID non trovato per {r['name']}")
        pid=match.group(1)
        if pid in ids: raise SystemExit(f"ERRORE: ID duplicato {pid}")
        ids.add(pid)
        if set(r["values"])!=COL_KEYS:
            raise SystemExit(f"ERRORE: colonne mancanti per {r['name']}: {set(r['values'])}")
        vals={k:(v if k=="sq" else int(v)) for k,v in r["values"].items()}
        out.append({"id":pid,"name":r["name"],"team_id":int(r["team_id"]),"team":vals["sq"],
                    "role":role,"mantra_roles":r["role_mantra"].split("|"),
                    "quotations":vals,"url":r["href"]})
    if counts!=ROLE_COUNTS: raise SystemExit(f"ERRORE: distribuzione ruoli inattesa: {counts}")
    payload={"season":EXPECTED_SEASON,
             "source":"https://www.fantacalcio.it/quotazioni-fantacalcio/2026-27",
             "player_count":len(out),"role_counts":counts,"players":out}
    Path(dst).write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(f"OK: {len(out)} giocatori; ruoli {counts}; ID univoci {len(ids)}; JSON creato")

if __name__=="__main__":
    if len(sys.argv)!=3: raise SystemExit("uso: parse_listone.py source.html listone.json")
    main(sys.argv[1],sys.argv[2])
