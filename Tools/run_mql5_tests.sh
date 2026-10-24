#!/usr/bin/env bash
# Run Scripts/SensitorAI/SensitorTests.mq5 inside a headless MT5 terminal (Linux + Wine + Xvfb).
# Prints the summary written by the script to Common\Files\SensitorAI\tests_result.txt
set -u
export WINEPREFIX="${WINEPREFIX:-/root/.wine-mt5}" WINEDEBUG=-all WINEDLLOVERRIDES="mscoree,mshtml="
export DISPLAY="${DISPLAY:-:50}"
MT5="${MT5_DIR:-$WINEPREFIX/drive_c/Program Files/MetaTrader 5}"
COMMON="$WINEPREFIX/drive_c/users/$(whoami)/AppData/Roaming/MetaQuotes/Terminal/Common/Files/SensitorAI"
pgrep -f "Xvfb $DISPLAY" >/dev/null || (Xvfb "$DISPLAY" -screen 0 1280x1024x24 >/dev/null 2>&1 &)
wineserver -k 2>/dev/null; sleep 1
mkdir -p "$MT5/MQL5/Presets"
printf 'InpCloseTerminal=true\r\n' > "$MT5/MQL5/Presets/SensitorTests.set"
printf '[StartUp]\r\nScript=SensitorAI\\SensitorTests\r\nScriptParameters=SensitorTests.set\r\nSymbol=EURUSD\r\nPeriod=H1\r\n' > "$MT5/tests.ini"
rm -f "$COMMON/tests_result.txt"
(cd "$MT5" && timeout 600 wine terminal64.exe /portable /config:tests.ini)
cat "$COMMON/tests_result.txt" 2>/dev/null || { echo "no result file"; exit 2; }
head -1 "$COMMON/tests_result.txt" | grep -q " 0 failed"
