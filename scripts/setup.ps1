# AI Incident Commander - Setup Script (Windows)
# Copy .env.example to .env and fill in your credentials

Write-Host "Setting up AI Incident Commander..." -ForegroundColor Green

# Copy environment file
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example - please fill in your credentials" -ForegroundColor Yellow
} else {
    Write-Host ".env already exists, skipping" -ForegroundColor Cyan
}

# Create virtual environment
if (-not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created Python virtual environment in .venv" -ForegroundColor Green
} else {
    Write-Host ".venv already exists, skipping" -ForegroundColor Cyan
}

# Install dependencies
& ".venv\Scripts\pip" install -r requirements.txt
Write-Host "Dependencies installed" -ForegroundColor Green

Write-Host "`nSetup complete! Run 'uvicorn app.main:app --reload' to start." -ForegroundColor Green
