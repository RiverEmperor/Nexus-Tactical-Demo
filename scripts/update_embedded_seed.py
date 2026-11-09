#!/usr/bin/env python3
"""Safely replace the embedded NEXUS Listone seed with a validated converted catalog."""
import json, sys
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit("usage: update_embedded_seed.py nexus-listone.json index.html")
catalog_path, index_path = map(Path, sys.argv[1:])
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
players = catalog.get("players")
if catalog.get("season") != "2026/27" or not isinstance(players, list) or len(players) < 500:
    raise SystemExit("ERRORE: catalogo non valido o incompleto")
ids = [str(p.get("officialId", "")) for p in players]
if any(not x for x in ids) or len(ids) != len(set(ids)):
    raise SystemExit("ERRORE: officialId mancanti o duplicati")
required = {"officialId","name","team","role","quote","quoteInitial","quoteDiff","quoteMantra","quoteMantraInitial","quoteMantraDiff","fvm","fvmMantra"}
for p in players:
    if not required.issubset(p) or p["role"] not in {"P","D","C","A"}:
        raise SystemExit("ERRORE: record NEXUS incompleto")
source = index_path.read_text(encoding="utf-8")
start_token = "const officialSeed="
end_token = ";\\nfunction stableListoneId"
start = source.find(start_token)
end = source.find(end_token, start)
if start < 0 or end < 0:
    raise SystemExit("ERRORE: blocco officialSeed non trovato; nessuna modifica eseguita")
seed = json.dumps(players, ensure_ascii=False, separators=(",", ":"))
updated = source[:start] + start_token + seed + source[end+1:]
index_path.write_text(updated, encoding="utf-8")
print(f"OK: seed incorporato aggiornato con {len(players)} giocatori; ID ufficiali univoci")
