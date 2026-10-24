# Sensitor AI watchdog for a Windows VPS (run every 5 minutes with the Task Scheduler).
# Alerts (Windows event log + optional e-mail) when the EA heartbeat is stale or reports ERROR_SAFE,
# and optionally restarts the terminal. It never trades and never changes the EA settings.
param(
  [string]$Tag = "XAUUSD_20250101",
  [string]$Common = "$env:APPDATA\MetaQuotes\Terminal\Common\Files\SensitorAI",
  [string]$Terminal = "C:\Program Files\MetaTrader 5\terminal64.exe",
  [int]$MaxAgeMinutes = 5,
  [switch]$Restart,
  [string]$SmtpServer = "", [string]$MailTo = "", [string]$MailFrom = ""
)
$hb = Join-Path $Common "$($Tag)_heartbeat.txt"
$msg = $null
if (-not (Test-Path $hb)) { $msg = "Sensitor AI: heartbeat file missing ($hb)" }
else {
  $age = (Get-Date) - (Get-Item $hb).LastWriteTime
  $line = Get-Content $hb -TotalCount 1
  if ($age.TotalMinutes -gt $MaxAgeMinutes) { $msg = "Sensitor AI: heartbeat stale ($([int]$age.TotalMinutes) min): $line" }
  elseif ($line -match "ERROR_SAFE") { $msg = "Sensitor AI: EA in ERROR_SAFE: $line" }
  elseif ($line -match ",0,\d+$") { $msg = "Sensitor AI: terminal reports no connection: $line" }
}
if ($msg) {
  if (-not [System.Diagnostics.EventLog]::SourceExists("SensitorAI")) { New-EventLog -LogName Application -Source "SensitorAI" }
  Write-EventLog -LogName Application -Source "SensitorAI" -EntryType Warning -EventId 1001 -Message $msg
  if ($SmtpServer -and $MailTo) { Send-MailMessage -SmtpServer $SmtpServer -To $MailTo -From $MailFrom -Subject "Sensitor AI alert" -Body $msg }
  if ($Restart -and -not (Get-Process terminal64 -ErrorAction SilentlyContinue)) { Start-Process $Terminal }
  Write-Output $msg
  exit 1
}
Write-Output "Sensitor AI: OK"
