#!/usr/bin/env bash
# Compile Sensitor AI with the official MetaEditor compiler (Windows, or Linux + Wine).
#
# Usage: Tools/compile_mql5.sh [file.mq5 ...]   (default: EA + test & tool scripts)
# Env:   MT5_DIR   MetaTrader 5 installation (portable mode) containing MetaEditor64.exe
#        WINEPREFIX Wine prefix where MT5 is installed
# The repository MQL5/ tree is mirrored into $MT5_DIR/MQL5 before compiling. Logs are written
# to Reports/compile/*.log and a summary is printed. Exit code != 0 if any file has errors.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export WINEPREFIX="${WINEPREFIX:-/root/.wine-mt5}"
export WINEDEBUG="${WINEDEBUG:--all}"
export WINEDLLOVERRIDES="${WINEDLLOVERRIDES:-mscoree,mshtml=}"
MT5_DIR="${MT5_DIR:-$WINEPREFIX/drive_c/Program Files/MetaTrader 5}"
OUT="$ROOT/Reports/compile"
mkdir -p "$OUT"

if [ ! -f "$MT5_DIR/MetaEditor64.exe" ]; then
  echo "MetaEditor64.exe not found in $MT5_DIR" >&2
  exit 2
fi

# mirror sources (Experts/Include/Scripts/Presets) into the terminal data folder
for d in Experts/SensitorAI Include/SensitorAI Scripts/SensitorAI; do
  mkdir -p "$MT5_DIR/MQL5/$d"
  rm -rf "$MT5_DIR/MQL5/$d"
  cp -r "$ROOT/MQL5/$d" "$MT5_DIR/MQL5/$d"
done

if [ "$#" -gt 0 ]; then
  FILES=("$@")
else
  FILES=("Experts/SensitorAI/SensitorAI.mq5")
  for f in "$ROOT"/MQL5/Scripts/SensitorAI/*.mq5; do
    [ -e "$f" ] && FILES+=("Scripts/SensitorAI/$(basename "$f")")
  done
fi

status=0
cd "$MT5_DIR"
for f in "${FILES[@]}"; do
  name="$(basename "$f" .mq5)"
  winpath="MQL5\\$(echo "$f" | sed 's#/#\\#g')"
  log="MQL5\\Logs_${name}.log"
  rm -f "MQL5/Logs_${name}.log"
  timeout 300 wine MetaEditor64.exe /portable /compile:"$winpath" /log:"$log" >/dev/null 2>&1
  if [ -f "MQL5/Logs_${name}.log" ]; then
    iconv -f UTF-16LE -t UTF-8 "MQL5/Logs_${name}.log" | tr -d '\r' | sed '1s/^\xEF\xBB\xBF//' > "$OUT/${name}.log"
  else
    echo "no log produced" > "$OUT/${name}.log"
  fi
  result="$(grep -E '^Result:' "$OUT/${name}.log" | tail -1)"
  echo "$f -> ${result:-NO RESULT}"
  if ! echo "$result" | grep -q ' 0 errors'; then
    status=1
    grep -E ': error|: warning' "$OUT/${name}.log" | head -40
  else
    grep -E ': warning' "$OUT/${name}.log" | head -40
  fi
  ex5="${f%.mq5}.ex5"
  [ -f "MQL5/$ex5" ] && cp "MQL5/$ex5" "$OUT/${name}.ex5" 2>/dev/null
done
exit $status
