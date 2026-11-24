#!/usr/bin/env python3
"""
Bandi Kode - opportunita rilevanti per Kode dal portale Sardegna CAT.

Scarica il feed RSS dei bandi in corso (multipagina), classifica ogni bando
per categorie Kode (AI, GIS/rilievo 3D, asset management/infrastrutture,
ottimizzazione, R&S, software/ICT), tiene solo quelli rilevanti e scrive
site/bandi.json usato dalla pagina pubblica su GitHub Pages.

Solo libreria standard Python. Nessun pip.
"""

import html as html_mod
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

# --- Feed Sardegna CAT ------------------------------------------------------

FEED_URL = "https://sardegnacat.regione.sardegna.it/portale/rss_bandi.asp"
FILTER_HIDE = "bScaduto=0 and tipo<>'Esito'"
ROWS_FOR_PAGE = 50
TIMEOUT = 30
USER_AGENT = "bandi-kode/1.0 (+https://github.com/andriatz/bandi-kode)"
AFS_NS = "http://www.aflink.it/XMLBANDI"

BASE_DIR = Path(__file__).resolve().parent
OUT_PATH = BASE_DIR / "site" / "bandi.json"

# --- Categorie Kode ------------------------------------------------------------

CATEGORIE = {
    "AI & Data Science": [
        "intelligenza artificiale", "artificial intelligence", "machine learning",
        "deep learning", "rete neurale", "reti neurali", "neural network",
        "natural language", "elaborazione del linguaggio", "large language model",
        "llm", "chatbot", "computer vision", "visione artificiale",
        "machine vision", "video analytics", "analisi video",
        "riconoscimento automatico", "analisi predittiva", "modello predittivo",
        "algoritmo predittivo", "data science", "scienza dei dati",
        "data analytics", "analisi dei dati", "analisi dati", "big data",
        "data mining", "data warehouse", "data lake", "business intelligence",
        "data visualization", "digital twin", "gemello digitale",
        "sistema informativo", "piattaforma dati", "open data", "data governance",
    ],
    "GIS & Rilievo 3D": [
        "gis", "arcgis", "webgis", "qgis",
        "sistema informativo territoriale",
        "sistemi informativi territoriali", "banca dati territoriale",
        "cartografico", "cartografia", "topografico", "geospazial", "geospatial",
        "geolocalizz", "georeferenz", "telerilevamento", "remote sensing",
        "lidar", "laser scanner", "scansione laser", "scansione 3d", "rilievo 3d",
        "nuvola di punti", "nuvole di punti", "point cloud", "mms",
        "mobile mapping", "fotogrammetria", "aerofotogrammetria", "ortofoto",
        "drone", "droni", "rpas", "satellitare", "gnss", "geodatabase",
        "modello 3d", "modelli 3d", "bim", "building information model",
    ],
    "Asset & Infrastrutture": [
        "asset management", "gestione patrimoniale", "gestione del patrimonio",
        "patrimonio infrastrutturale", "patrimonio immobiliare",
        "patrimonio urbano", "inventario asset", "censimento patrimoniale",
        "censimento infrastrutture", "censimento del patrimonio",
        "facility management", "manutenzione predittiva", "predictive maintenance",
        "monitoraggio strutturale", "sensoristica", "iot", "internet of things",
        "gestione infrastrutture", "gestione delle infrastrutture",
        "smart city", "smart region",
    ],
    "Ottimizzazione & Simulazione": [
        "ottimizzazione", "simulazione", "ricerca operativa",
        "operations research", "supply chain", "catena di fornitura",
        "logistica", "gestione flotta", "fleet management", "scheduling",
        "pianificazione dei trasporti", "pianificazione della mobilita",
        "mobilita", "gestione del traffico", "regolazione del traffico",
        "gestione magazzino", "warehouse",
    ],
    "Software & ICT": [
        "software", "applicativo", "piattaforma digitale", "applicazione web",
        "portale web", "servizi digitali", "digitalizzazione",
        "trasformazione digitale", "ict", "information technology", "cloud",
        "cybersecurity", "cybersicurezza", "sicurezza informatica",
        "blockchain", "data center", "centro dati", "industria 4.0",
        "automazione", "robotica", "realta virtuale", "realta aumentata",
        "realta estesa", "banda larga", "broadband", "infrastruttura telematica",
        "infrastruttura di rete", "rete di telecomunicazione", "5g",
    ],
}

# Prefissi CPV -> categoria aggiunta se il codice inizia con il prefisso.
CPV_PREFIX_CATEGORIE = {
    "48": "Software & ICT",
    "72": "Software & ICT",
    "731": "R&S e Innovazione",
    "732": "R&S e Innovazione",
}


# --- Normalizzazione e matching (riuso dell'approccio dello script originale) --

def strip_accents(text):
    text = text.lower()
    repl = {
        "\u00e0": "a", "\u00e1": "a",
        "\u00e8": "e", "\u00e9": "e", "\u00ea": "e",
        "\u00ec": "i", "\u00ed": "i", "\u00ee": "i",
        "\u00f2": "o", "\u00f3": "o", "\u00f4": "o",
        "\u00f9": "u", "\u00fa": "u",
        "\u2019": "", "\u2018": "", "\u02bc": "",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text


def kw_matches(kw, text):
    """Keyword multi-parola o lunghe: sottostringa. Acronimi corti: confine parola."""
    if " " in kw or len(kw) > 4:
        return kw in text
    pattern = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def cpv_code(cpv_text):
    if not cpv_text:
        return ""
    m = re.match(r"\s*(\d+)", cpv_text)
    return m.group(1) if m else ""


def classify(record):
    """Categoria(i) Kode per un bando. Lista vuota = non rilevante."""
    text = strip_accents((record["oggetto"] or "") + " " + (record["cpv"] or ""))
    matched = []
    for label, kws in CATEGORIE.items():
        if any(kw_matches(strip_accents(kw), text) for kw in kws):
            matched.append(label)
    code = cpv_code(record["cpv"])
    if code:
        for pfx, label in CPV_PREFIX_CATEGORIE.items():
            if code.startswith(pfx) and label not in matched:
                matched.append(label)
    # "Software & ICT" da solo (solo CPV) resta un match debole:
    # lo teniamo, ordina comunque le categorie forti prima.
    return matched


# --- Parsing XML -----------------------------------------------------------------

def _text(item, tag, ns=AFS_NS):
    el = item.find(f"{{{ns}}}{tag}") if ns else item.find(tag)
    if el is None or el.text is None:
        return ""
    return el.text.strip()


def clean_html(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_mod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def parse_rss(xml_text):
    root = ET.fromstring(xml_text)
    channel = root.find("channel")
    if channel is None:
        return [], None
    tot_record = None
    tot_el = channel.find(f"{{{AFS_NS}}}totRecord")
    if tot_el is not None and tot_el.text:
        try:
            tot_record = int(tot_el.text.strip())
        except ValueError:
            tot_record = None
    items = []
    for it in channel.findall("item"):
        link = _text(it, "link", ns=None).replace(" ", "").replace(
            "/portale/", "/portalegare/"
        )
        record = {
            "id": _text(it, "IdMsg"),
            "oggetto": clean_html(_text(it, "Oggetto")),
            "contratto": _text(it, "Contratto"),
            "ente_proponente": _text(it, "EnteProponente"),
            "denominazione_ente": _text(it, "DenominazioneEnte"),
            "importo": _text(it, "a_base_asta"),
            "scadenza": _text(it, "DtScadenzaBandoTecnical"),
            "pubblicazione": _text(it, "DtPubblicazioneTecnical"),
            "cpv": _text(it, "CPV"),
            "tipo_procedura": _text(it, "TipoProcedura"),
            "link": link,
        }
        if record["id"]:
            items.append(record)
    return items, tot_record


# --- Fetch ------------------------------------------------------------------------

def fetch_page(page):
    params = {
        "FilterHide": FILTER_HIDE,
        "numRowForPag": ROWS_FOR_PAGE,
        "nPag": page,
    }
    url = f"{FEED_URL}?{urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_all_items():
    all_items = []
    page = 1
    total_records = None
    while True:
        xml_text = fetch_page(page)
        items, total_records = parse_rss(xml_text)
        all_items.extend(items)
        print(f"  pagina {page}: {len(items)} record (totale: {len(all_items)})", flush=True)
        if not items:
            break
        if total_records is not None and len(all_items) >= total_records:
            break
        page += 1
        time.sleep(0.3)
    return all_items, total_records


# --- Main -------------------------------------------------------------------------

def scadenza_key(rec):
    s = rec.get("scadenza") or ""
    return s[:19] if s else "9999-12-31T23:59:59"


def main():
    print(f"=== Bandi Kode - {datetime.now().isoformat(timespec='seconds')} ===")
    print("[1/3] Download feed RSS Sardegna CAT...")
    items, total = fetch_all_items()
    print(f"  Scaricati {len(items)} bandi (dichiarati: {total})")

    # Snapshot precedente: serve per marcare i "nuovi".
    prev_ids = set()
    if OUT_PATH.exists():
        try:
            prev = json.loads(OUT_PATH.read_text(encoding="utf-8"))
            prev_ids = {b["id"] for b in prev.get("bandi", [])}
        except (json.JSONDecodeError, KeyError):
            prev_ids = set()

    print("[2/3] Classificazione Kode...")
    bandi = []
    for rec in items:
        categorie = classify(rec)
        if not categorie:
            continue
        b = {
            "id": rec["id"],
            "oggetto": rec["oggetto"],
            "ente": rec["denominazione_ente"] or rec["ente_proponente"] or "n/d",
            "importo": rec["importo"],
            "scadenza": rec["scadenza"],
            "pubblicazione": rec["pubblicazione"],
            "cpv": rec["cpv"],
            "tipo_procedura": rec["tipo_procedura"],
            "contratto": rec["contratto"],
            "link": rec["link"],
            "categorie": categorie,
            "nuovo": rec["id"] not in prev_ids,
        }
        bandi.append(b)
    bandi.sort(key=scadenza_key)
    n_nuovi = sum(1 for b in bandi if b["nuovo"])

    print(f"  Rilevanti Kode: {len(bandi)} su {len(items)} | nuovi: {n_nuovi}")

    print("[3/3] Scrittura site/bandi.json...")
    out = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tot_bandi_portale": len(items),
        "tot_rilevanti": len(bandi),
        "nuovi": n_nuovi,
        "bandi": bandi,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"  Salvato: {OUT_PATH}")
    print("---")
    print(f"OK: {len(bandi)} opportunita Kode ({n_nuovi} nuove).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
