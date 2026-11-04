#!/usr/bin/env python3
"""Convert validated official 2026/27 Listone JSON to the NEXUS app seed schema."""
from __future__ import annotations
import json, sys
from pathlib import Path

SEASON = "2026/27"
ROLES = {"p":"P", "d":"D", "c":"C", "a":"A"}

def convert(source: Path, target: Path) -> dict:
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("season") != SEASON or not isinstance(data.get("players"), list):
        raise SystemExit("ERRORE: input Listone non valido o stagione inattesa")
    converted = []
    seen = set()
    for row in data["players"]:
        pid = str(row.get("id", "")).strip()
        name = str(row.get("name", "")).strip()
        role = ROLES.get(str(row.get("role", "")).lower())
        q = row.get("quotations") or {}
        required = ("c_qi", "c_qa", "c_fvm", "m_qi", "m_qa", "m_fvm")
        if not pid or not name or not role or any(k not in q for k in required):
            raise SystemExit(f"ERRORE: record incompleto: {name or pid or 'sconosciuto'}")
        if pid in seen:
            raise SystemExit(f"ERRORE: ID duplicato: {pid}")
        seen.add(pid)
        converted.append({
            "officialId": pid,
            "id": f"fc:{SEASON.replace('/', '-') }:{pid}",
            "name": name,
            "team": str(row.get("team", "")).strip(),
            "role": role,
            "mantra": "/".join(row.get("mantra_roles") or []),
            "quote": int(q["c_qa"]),
            "quoteInitial": int(q["c_qi"]),
            "quoteDiff": int(q["c_qa"]) - int(q["c_qi"]),
            "quoteMantra": int(q["m_qa"]),
            "quoteMantraInitial": int(q["m_qi"]),
            "quoteMantraDiff": int(q["m_qa"]) - int(q["m_qi"]),
            "fvm": int(q["c_fvm"]),
            "fvmMantra": int(q["m_fvm"]),
        })
    if len(converted) != data.get("player_count") or len(converted) < 500:
        raise SystemExit("ERRORE: conteggio giocatori non coerente; conversione bloccata")
    result = {"season": SEASON, "source": data.get("source"), "player_count": len(converted), "players": converted}
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\\n", encoding="utf-8")
    print(f"OK: {len(converted)} giocatori convertiti; ID ufficiali univoci; schema NEXUS pronto")
    return result

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("uso: convert_listone.py listone.json nexus-listone.json")
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
