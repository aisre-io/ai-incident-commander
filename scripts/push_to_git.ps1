#Requires -Version 5.1
<#
.SYNOPSIS
    One-shot helper to push the AI Incident Commander repo.

.DESCRIPTION
    Pushes to ALL configured remotes (Gitee primary, GitHub optional).
    Auto-detects the current branch (main vs master).
    Walks through git init -> add -> commit -> push to all remotes.

.EXAMPLE
    pwsh -File scripts/push_to_git.ps1

.NOTES
    Primary remote: https://gitee.com/ai-sre/ai-incident-commander.git
    Optional:       https://github.com/ai-sre/ai-incident-commander.git (add via: git remote add github <url>)
#>

$ErrorActionPreference = "Stop"
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

Write-Host ""
Write-Host "=== Push to Git (Gitee primary, GitHub optional) ===" -ForegroundColor Cyan
Write-Host "Repo root: $(Get-Location)"
Write-Host ""

# 1. Check git
$git = Get-Command git -ErrorAction SilentlyContinue
if (-not $git) {
    Write-Host "::ERROR:: git not found on PATH. Install from https://git-scm.com" -ForegroundColor Red
    exit 1
}

# 2. Sanity: make sure .env is in .gitignore
$envFile = Join-Path (Get-Location) ".env"
$gitignorePath = Join-Path (Get-Location) ".gitignore"
if (Test-Path $envFile) {
    $gitignore = Get-Content $gitignorePath -Raw -ErrorAction SilentlyContinue
    if ($gitignore -notmatch "^\.env$") {
        Write-Host "::WARN:: .env exists but .gitignore has no '.env' entry. Fixing..." -ForegroundColor Yellow
        Add-Content $gitignorePath "`n.env`n.env.*`n!.env.example"
    } else {
        Write-Host "[OK] .env is in .gitignore" -ForegroundColor Green
    }
}

# 3. git init if needed
if (-not (Test-Path (Join-Path (Get-Location) ".git"))) {
    Write-Host "[..] Initializing git repo (branch: main)"
    git init -b main | Out-Null
    Write-Host "[OK] git init done" -ForegroundColor Green
} else {
    Write-Host "[OK] git repo already initialized" -ForegroundColor Green
}

# 4. Check git user config
$userName = git config user.name 2>$null
$userEmail = git config user.email 2>$null
if (-not $userName -or -not $userEmail) {
    Write-Host ""
    Write-Host "Git user.name / user.email are not set. Using repo-local values for this push only." -ForegroundColor Yellow
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

# 5. Detect current branch
$currentBranch = git branch --show-current 2>$null
if (-not $currentBranch) { $currentBranch = "main" }
Write-Host "[..] Current branch: $currentBranch"

# 6. Stage and review
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

# 7. Commit
$commitMsg = Read-Host "Commit message [Update AI Incident Commander]"
if ([string]::IsNullOrWhiteSpace($commitMsg)) {
    $commitMsg = "Update AI Incident Commander"
}
git commit -m "$commitMsg" | Out-Null
Write-Host "[OK] Commit created" -ForegroundColor Green

# 8. Push to all configured remotes
$remotes = git remote
if (-not $remotes) {
    Write-Host ""
    Write-Host "No remotes configured. Add one with:" -ForegroundColor Yellow
    Write-Host "  git remote add origin https://gitee.com/ai-sre/ai-incident-commander.git"
    exit 1
}

$pushOk = $true
foreach ($remote in $remotes) {
    $url = git remote get-url $remote
    Write-Host ""
    Write-Host "[..] pushing to $remote ($url)" -ForegroundColor Cyan
    git push -u $remote $currentBranch 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] pushed to $remote" -ForegroundColor Green
    } else {
        Write-Host "::ERROR:: push to $remote failed (exit $LASTEXITCODE)" -ForegroundColor Red
        $pushOk = $false
    }
}

if ($pushOk) {
    Write-Host ""
    Write-Host "=== DONE ===" -ForegroundColor Green
    Write-Host "Live URLs:"
    foreach ($remote in $remotes) {
        $url = git remote get-url $remote
        if ($url -match "gitee\.com") {
            Write-Host "  Gitee:  https://gitee.com/ai-sre/ai-incident-commander" -ForegroundColor Cyan
        } elseif ($url -match "github\.com") {
            Write-Host "  GitHub: https://github.com/ai-sre/ai-incident-commander" -ForegroundColor Cyan
        }
    }
} else {
    Write-Host ""
    Write-Host "::ERROR:: One or more pushes failed. Common causes:" -ForegroundColor Red
    Write-Host "  - Need to authenticate (use a Personal Access Token as password if 2FA is on)"
    Write-Host "  - Branch name mismatch (this script uses '$currentBranch')"
    Write-Host "  - Network/firewall (esp. for github.com in mainland China)"
}
