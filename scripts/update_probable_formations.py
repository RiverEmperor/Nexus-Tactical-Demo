#!/usr/bin/env python3
"""Aggiorna il feed NEXUS delle probabili formazioni da SOS Fanta.

Il file prodotto contiene solo dati essenziali: modulo, XI, panchina,
avversaria, orario della partita e probabilità pubblicate dalla fonte.
Se la pagina cambia struttura o i dati sono incompleti, il programma fallisce
senza sovrascrivere il feed precedente.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URL = "https://www.sosfanta.com/lista-formazioni/probabili-formazioni-serie-a/"
EXPECTED_TEAMS = 20
GROUPS = {"Titolari": "starters", "Panchina": "bench"}


def clean(value):
    return " ".join((value or "").split())


def parse_player(li):
    value = clean(li.get_text(" ", strip=True))
    match = re.match(r"^(\d{1,3})%\s*(.+)$", value)
    if match:
        return {"name": clean(match.group(2)), "probability": int(match.group(1))}
    if value:
        return {"name": value, "probability": None}
    return None


def parse_article(article):
    team_heads = [clean(h.get_text(" ", strip=True)) for h in article.find_all("h2")]
    if len(team_heads) != 2:
        return None

    article_text = clean(article.get_text(" ", strip=True))
    date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}:\d{2})", article_text)
    match_date = (date_match.group(1) + " " + date_match.group(2)) if date_match else None

    modules = {}
    for team in team_heads:
        m = re.search(re.escape(team) + r"\s+(\d(?:-\d){2,3})", article_text)
        modules[team] = m.group(1) if m else "4-3-3"

    groups = {}
    for heading in article.find_all("h3"):
        label = clean(heading.get_text(" ", strip=True))
        if label not in GROUPS:
            continue
        section = heading.find_parent("section")
        lists = section.find_all("ul") if section else []
        if len(lists) != 2:
            raise ValueError(f"Struttura {label} non riconosciuta per {team_heads}")
        groups[label] = [
            [p for p in (parse_player(li) for li in ul.find_all("li", recursive=False)) if p]
            for ul in lists
        ]

    if set(groups) != set(GROUPS):
        raise ValueError(f"Sezioni titolari/panchina mancanti per {team_heads}")

    result = {}
    for index, team in enumerate(team_heads):
        starters = groups["Titolari"][index]
        bench = groups["Panchina"][index]
        if len(starters) != 11:
            raise ValueError(f"{team}: attesi 11 titolari, trovati {len(starters)}")
        if not bench:
            raise ValueError(f"{team}: panchina vuota")
        result[team] = {
            "module": modules[team],
            "opponent": team_heads[1 - index],
            "matchDate": match_date,
            "starters": starters,
            "bench": bench,
        }
    return result


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "alpha-test/formazioni.json")
    response = requests.get(
        SOURCE_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; NEXUS-Tactical/1.0)"},
        timeout=45,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    teams = {}
    for article in soup.find_all("article"):
        parsed = parse_article(article)
        if parsed:
            overlap = set(teams).intersection(parsed)
            if overlap:
                raise ValueError(f"Squadre duplicate: {sorted(overlap)}")
            teams.update(parsed)

    if len(teams) != EXPECTED_TEAMS:
        raise ValueError(f"Attese {EXPECTED_TEAMS} squadre, trovate {len(teams)}")
    for name, team in teams.items():
        if len(team["starters"]) != 11 or not team["bench"]:
            raise ValueError(f"Dati incompleti per {name}")

    payload = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "SOS Fanta",
        "sourceUrl": SOURCE_URL,
        "teams": dict(sorted(teams.items(), key=lambda item: item[0].casefold())),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Feed NEXUS aggiornato: {len(teams)} squadre")
    for name, team in teams.items():
        print(f"- {name}: {team['module']} · XI {len(team['starters'])} · panchina {len(team['bench'])}")


if __name__ == "__main__":
    main()
