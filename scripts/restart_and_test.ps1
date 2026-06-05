$ErrorActionPreference = "Continue"
Set-Location 'D:\Jacky\AI-Native DevOps\ai-incident-commander'

# Kill existing server (PIDs from previous run)
Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue |
  ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# Clean logs
Remove-Item '.\out\server.log','.\out\server.err.log' -ErrorAction SilentlyContinue

# Start fresh server (loads fixed lark_bot.py)
Start-Process -FilePath '.\.venv\Scripts\python.exe' `
  -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000' `
  -RedirectStandardOutput '.\out\server.log' `
  -RedirectStandardError '.\out\server.err.log' `
  -NoNewWindow

Start-Sleep -Seconds 4

Write-Output "=== Health check ==="
try {
  $r = Invoke-WebRequest http://127.0.0.1:8000/health -UseBasicParsing
  Write-Output "HTTP $($r.StatusCode): $($r.Content)"
} catch {
  Write-Output "FAILED: $_"
  exit 1
}

Write-Output ""
Write-Output "=== Trigger e2e test ==="
& '.\.venv\Scripts\python.exe' simulation/send_test_incident.py 2>&1

Write-Output ""
Write-Output "=== Server stdout (last 20) ==="
if (Test-Path '.\out\server.log') {
  Get-Content '.\out\server.log' -Tail 20
}

Write-Output ""
Write-Output "=== Server stderr (last 30) ==="
if (Test-Path '.\out\server.err.log') {
  Get-Content '.\out\server.err.log' -Tail 30
}
