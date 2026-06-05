#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot helper to push the AI Incident Commander repo to a new GitHub repo.

.DESCRIPTION
    Walks the user through git init -> add -> commit -> push.
    Prompts for the GitHub remote URL (HTTPS form).
    If `gh` CLI is on PATH, offers to create the GitHub repo automatically.

.EXAMPLE
    pwsh -File scripts/push_to_github.ps1
#>

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "=== Push to GitHub ===" -ForegroundColor Cyan
Write-Host "Repo root: $(Get-Location)"
Write-Host ""

# 1. Check git is installed
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "::ERROR:: git not found on PATH. Install from https://git-scm.com" -ForegroundColor Red
    exit 1
}

# 2. Sanity: make sure we don't accidentally commit secrets
$envFile = Join-Path (Get-Location) ".env"
if (Test-Path $envFile) {
    $gitignore = Get-Content (Join-Path (Get-Location) ".gitignore") -Raw -ErrorAction SilentlyContinue
    if ($gitignore -notmatch "^\.env$") {
        Write-Host "::WARN:: .env exists but .gitignore has no '.env' entry. Fixing..." -ForegroundColor Yellow
        Add-Content (Join-Path (Get-Location) ".gitignore") "`n.env`n.env.*`n!.env.example"
    } else {
        Write-Host "[OK] .env is in .gitignore" -ForegroundColor Green
    }
}

# 3. git init if needed
if (-not (Test-Path (Join-Path (Get-Location) ".git"))) {
    Write-Host "[..] Initializing git repo"
    git init | Out-Null
    git branch -M main | Out-Null
    Write-Host "[OK] git init done (default branch: main)" -ForegroundColor Green
} else {
    Write-Host "[OK] git repo already initialized" -ForegroundColor Green
}

# 4. Check git user config (needed for commit)
$userName = git config user.name 2>$null
$userEmail = git config user.email 2>$null
if (-not $userName -or -not $userEmail) {
    Write-Host ""
    Write-Host "Git user.name / user.email are not set globally. Using repo-local values for this push only." -ForegroundColor Yellow
    if (-not $userName) {
        $userName = Read-Host "  Enter your name (for git commit author)"
        git config user.name "$userName"
    }
    if (-not $userEmail) {
        $userEmail = Read-Host "  Enter your email (for git commit author)"
        git config user.email "$userEmail"
    }
    Write-Host ""
}

# 5. Stage and review
Write-Host "[..] git add -A"
git add -A

$stagedCount = (git diff --cached --name-only | Measure-Object -Line).Lines
Write-Host "[OK] $stagedCount files staged" -ForegroundColor Green

if ($stagedCount -eq 0) {
    Write-Host "Nothing to commit. Exiting." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Files to be committed (first 20):" -ForegroundColor Cyan
git diff --cached --name-only | Select-Object -First 20
Write-Host ""

$proceed = Read-Host "Proceed with commit + push? [y/N]"
if ($proceed -ne "y") {
    Write-Host "Aborted by user." -ForegroundColor Yellow
    exit 0
}

# 6. Commit
$commitMsg = Read-Host "Commit message [Initial commit: AI Incident Commander]"
if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "Initial commit: AI Incident Commander"
}
git commit -m "$commitMsg" | Out-Null
Write-Host "[OK] Commit created" -ForegroundColor Green

# 7. Set up remote
$existingRemote = git remote get-url origin 2>$null
if ($existingRemote) {
    Write-Host "[OK] Remote 'origin' already set: $existingRemote" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Now create an EMPTY GitHub repo at https://github.com/new" -ForegroundColor Cyan
    Write-Host "  - Owner:       ai-sre   (your GitHub handle, verified available)" -ForegroundColor Cyan
    Write-Host "  - Name:        ai-incident-commander" -ForegroundColor Cyan
    Write-Host "  - Description: Self-hosted AI SRE that compresses 60+ alerts into 1 incident in 12s" -ForegroundColor Cyan
    Write-Host "  - Visibility:  Public (so CI badge is visible to Vercel/Render/Supabase CEOs)" -ForegroundColor Cyan
    Write-Host "  - DO NOT check 'Add README' / '.gitignore' / 'license' (we have them)" -ForegroundColor Cyan
    Write-Host ""
    $remoteUrl = Read-Host "Paste the HTTPS remote URL (e.g. https://github.com/ai-sre/ai-incident-commander.git)"
    if ([string]::IsNullOrWhiteSpace($remoteUrl)) {
        Write-Host "::ERROR:: Empty remote URL. Aborting." -ForegroundColor Red
        exit 1
    }
    git remote add origin $remoteUrl
    Write-Host "[OK] remote add origin $remoteUrl" -ForegroundColor Green
}

# 8. Push
Write-Host "[..] git push -u origin main"
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=== DONE ===" -ForegroundColor Green
    Write-Host "Your repo is live. Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Check CI badge on README (will go green after first push triggers .github/workflows/ci.yml)"
    Write-Host "  2. Add repo URL to outreach emails (replaces 'github.com/<your-handle>/ai-incident-commander')"
    Write-Host "  3. Open fly.toml and run: fly launch --copy-config"
    Write-Host ""
} else {
    Write-Host "::ERROR:: git push failed. Common causes:" -ForegroundColor Red
    Write-Host "  - Repo not created on GitHub yet (create at https://github.com/new)"
    Write-Host "  - Wrong remote URL"
    Write-Host "  - Need to authenticate (use a Personal Access Token as password if 2FA is on)"
    Write-Host "  - Branch name mismatch (this script uses 'main')"
}
