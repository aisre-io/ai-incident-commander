$ErrorActionPreference = "Continue"
Set-Location 'D:\Jacky\AI-Native DevOps\ai-incident-commander'

# Read webhook URL from .env
$envContent = Get-Content '.\.env' -Raw
$urlLine = ($envContent -split "`n" | Where-Object { $_ -match '^LARK_WEBHOOK_URL=' } | Select-Object -First 1)
$url = ($urlLine -replace '^LARK_WEBHOOK_URL=', '').Trim()

Write-Output "=== Test 1: Direct Lark webhook test (no server) ==="
Write-Output "URL: $url"
$body = '{"msg_type":"text","content":{"text":"[Direct test] Webhook is alive"}}'
try {
  $r = Invoke-RestMethod -Method Post -Uri $url -ContentType "application/json" -Body $body -TimeoutSec 10
  Write-Output "Response: $($r | ConvertTo-Json -Compress)"
} catch {
  Write-Output "FAILED: $($_.Exception.Message)"
}

Write-Output ""
Write-Output "=== Test 2: Trigger server webhook ==="
$python = '.\.venv\Scripts\python.exe'
& $python simulation/send_test_incident.py 2>&1

Write-Output ""
Write-Output "=== Test 3: Server stdout log (last 30 lines) ==="
if (Test-Path '.\out\server.log') {
  Get-Content '.\out\server.log' -Tail 30
} else {
  Write-Output "(no server.log)"
}

Write-Output ""
Write-Output "=== Test 4: Server stderr log (last 30 lines) ==="
if (Test-Path '.\out\server.err.log') {
  Get-Content '.\out\server.err.log' -Tail 30
} else {
  Write-Output "(no server.err.log)"
}
