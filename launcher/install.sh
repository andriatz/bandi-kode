#!/usr/bin/env bash
# Launcher "Bandi Kode" per Linux: scarica icona e crea il file .desktop
# dell'utente. Nessun permesso di root. Rimuovibile con: rm dei due file.
set -uo pipefail

PAGE="https://andriatz.github.io/bandi-kode/"
RAW="https://raw.githubusercontent.com/andriatz/bandi-kode/main/launcher"
APPS_DIR="$HOME/.local/share/applications"
ICONS_DIR="$HOME/.local/share/icons"
DESKTOP="$APPS_DIR/bandi-kode.desktop"
ICON="$ICONS_DIR/bandi-kode.svg"

mkdir -p "$APPS_DIR" "$ICONS_DIR"

echo "Scarico l'icona..."
if ! curl -fsSL "$RAW/bandi-kode.svg" -o "$ICON"; then
  echo "  (download fallito: uso l'icona incorporata)"
  cat > "$ICON" <<'EOF'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="28" fill="#0f1115"/>
  <path d="M34 28 h16 v30 l24 -30 h20 l-28 34 l30 38 h-20 l-26 -33 v33 h-16 z" fill="#e8eaed"/>
  <circle cx="102" cy="102" r="12" fill="#4f8cff"/>
</svg>
EOF
fi

echo "Creo il launcher..."
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Name=Bandi Kode
Comment=Opportunita di gara rilevanti Kode - Portale Sardegna CAT
Exec=xdg-open $PAGE
Icon=$ICON
Terminal=false
Categories=Utility;Office;
Keywords=bandi;gare;kode;sardegna;opportunita;
StartupNotify=false
X-GNOME-UsesNotifications=false
EOF

command -v update-desktop-database >/dev/null 2>&1 \
  && update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Fatto: \"Bandi Kode\" nel menu applicazioni."
echo "Per rimuoverlo: rm $DESKTOP $ICON"
