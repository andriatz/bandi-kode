# Bandi Kode

Le opportunita di gara rilevanti per Kode dal Portale Acquisti della Regione
Sardegna ([Sardegna CAT](https://sardegnacat.regione.sardegna.it)), sempre
sottomano: web, mobile, con filtri per area Kode.

**Apri: <https://andriatz.github.io/bandi-kode/>**

## Come si aggiorna

Premi **"Aggiorna ora"** in alto a destra nella pagina: si apre il workflow
GitHub gia autenticato, clicca **"Run workflow"** e dopo circa un minuto la
pagina si ricarica da sola.

## Installalo su ogni dispositivo

**Linux** — una riga da terminale, nessun permesso di root, crea "Bandi Kode"
nel menu applicazioni:

```bash
curl -fsSL https://raw.githubusercontent.com/andriatz/bandi-kode/main/launcher/install.sh | bash
```

Se la voce non compare subito nel menu, riavvia la sessione o dai
`update-desktop-database ~/.local/share/applications`. Per rimuoverlo:
`rm ~/.local/share/applications/bandi-kode.desktop ~/.local/share/icons/bandi-kode.svg`

**Telefono** — apri la pagina nel browser e usa "Aggiungi alla schermata
Home" (Android) o "Aggiungi a Home" (iOS): si comporta come un'app.

## Cosa resta dentro

Un bando entra nella pagina solo se matcha almeno una categoria Kode:

- **AI & Data Science** — machine learning, computer vision, video analytics,
  predictive analytics, data science, digital twin...
- **GIS & Rilievo 3D** — GIS, LiDAR, nuvole di punti, MMS / mobile mapping,
  fotogrammetria, droni, ortofoto, telerilevamento, BIM...
- **Asset & Infrastrutture** — asset management, manutenzione predittiva,
  censimenti patrimoniali, monitoraggio strutturale, IoT, smart city...
- **Ottimizzazione & Simulazione** — ottimizzazione, simulazione, logistica,
  flotte, mobilita e traffico, supply chain...
- **R&S e Innovazione** — match per codice CPV della ricerca (73x, 732...)
- **Software & ICT** — piattaforme digitali, cloud, cybersecurity, CPV 48/72...

I match avvengono su oggetto del bando e CPV; i codici CPV 48/72 (software e
servizi IT) vengono considerati un segnale debole.

## Come funziona dentro

```
bottone "Aggiorna" (workflow_dispatch)
   -> GitHub Actions esegue monitor.py
      -> scarica il feed RSS Sardegna CAT (multipagina, solo bandi in corso)
      -> classifica keyword + CPV, filtra le opportunita Kode
      -> marca "NUOVI" rispetto allo snapshot precedente
      -> committa site/bandi.json
   -> pubblica site/ su GitHub Pages
   -> la pagina fa polling e si ricarica da sola quando arrivano dati nuovi
```

- `monitor.py` — sole librerie standard Python, zero dipendenze.
- `site/index.html` — pagina statica (CSS/JS inline), cerca, filtri per
  categoria, "solo NUOVI", ordinamenti, reminder scadenza con colori.
- `site/bandi.json` — snapshot dei dati generato dall'ultimo giro (serve pure
  come stato per calcolare i "nuovi" del giro dopo).
- `.github/workflows/update.yml` — un solo job: scarica, committa, pubblica.

## Aggiungere o ritoccare le keyword

Le categorie e le keyword stanno in `monitor.py` nel dizionario `CATEGORIE`
(piu `CPV_PREFIX_CATEGORIE` per i codici CPV). Modifica e pusha: parte il
workflow e la pagina si rigenera da sola.

_Per un aggiornamento automatico giornaliero basta aggiungere `schedule` con
`cron` nel workflow — volutamente lasciato fuori: aggiornamento solo manuale._
