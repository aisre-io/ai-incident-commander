$ErrorActionPreference = "Stop"
Set-Location 'D:\Jacky\AI-Native DevOps\ai-incident-commander'
Remove-Item '.\out\server.log','.\out\server.err.log' -ErrorAction SilentlyContinue

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
}
