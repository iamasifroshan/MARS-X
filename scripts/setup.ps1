#Requires -Version 5.1
<#
.SYNOPSIS
    MARS-X Development Environment Setup Script

.DESCRIPTION
    Checks prerequisites, creates the Python virtual environment, and installs
    all backend and frontend dependencies for the MARS-X platform.

.NOTES
    Run from the repository root:  .\scripts\setup.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ──────────────────────────────────────────────────────────────────────
$RepoRoot   = Split-Path -Parent $PSScriptRoot          # E:\MARS-X
$Backend    = Join-Path $RepoRoot "backend"
$Frontend   = Join-Path $RepoRoot "frontend"
$VenvDir    = Join-Path $Backend  ".venv"
$VenvPip    = Join-Path $VenvDir  "Scripts\pip.exe"
$VenvPython = Join-Path $VenvDir  "Scripts\python.exe"
$ReqFile    = Join-Path $Backend  "requirements.txt"

# ── Helpers ────────────────────────────────────────────────────────────────────
function Write-Header([string]$text) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor DarkCyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor DarkCyan
}

function Write-Step([string]$text) {
    Write-Host "  → $text" -ForegroundColor Gray
}

function Write-Ok([string]$text) {
    Write-Host "  ✔ $text" -ForegroundColor Green
}

function Write-Warn([string]$text) {
    Write-Host "  ⚠ $text" -ForegroundColor Yellow
}

function Write-Fail([string]$text) {
    Write-Host "  ✖ $text" -ForegroundColor Red
}

# ── Status trackers ────────────────────────────────────────────────────────────
$pythonOk   = $false
$nodeOk     = $false
$venvOk     = $false
$backendOk  = $false
$frontendOk = $false

# ══════════════════════════════════════════════════════════════════════════════
Write-Header "MARS-X Setup"
Write-Host "  Repository: $RepoRoot"
Write-Host ""

# ── 1. Check Python ───────────────────────────────────────────────────────────
Write-Header "1/5  Checking Python"
try {
    $pyVersion = & py --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "py launcher returned exit code $LASTEXITCODE" }
    Write-Ok "Python found: $pyVersion"
    $pythonOk = $true
} catch {
    Write-Fail "Python 'py' launcher not found."
    Write-Warn "Install Python 3.12+ from https://www.python.org/"
    Write-Warn "Ensure 'py' launcher is enabled during installation."
}

# ── 2. Check Node.js ──────────────────────────────────────────────────────────
Write-Header "2/5  Checking Node.js"
try {
    $nodeVersion = & node --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "node returned exit code $LASTEXITCODE" }
    Write-Ok "Node.js found: $nodeVersion"
    $nodeOk = $true
} catch {
    Write-Fail "Node.js not found."
    Write-Warn "Install Node.js 18+ from https://nodejs.org/"
}

# ── 3. Create backend venv ────────────────────────────────────────────────────
Write-Header "3/5  Backend Virtual Environment"
if (-not $pythonOk) {
    Write-Warn "Skipped — Python not available."
} elseif (Test-Path $VenvPython) {
    Write-Ok "Virtual environment already exists at $VenvDir"
    $venvOk = $true
} else {
    Write-Step "Creating virtual environment at $VenvDir ..."
    try {
        & py -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed with exit code $LASTEXITCODE" }
        Write-Ok "Virtual environment created."
        $venvOk = $true
    } catch {
        Write-Fail "Failed to create virtual environment: $_"
    }
}

# ── 4. Install backend dependencies ───────────────────────────────────────────
Write-Header "4/5  Backend Dependencies"
if (-not $venvOk) {
    Write-Warn "Skipped — virtual environment not available."
} elseif (-not (Test-Path $ReqFile)) {
    Write-Warn "requirements.txt not found at $ReqFile"
} else {
    Write-Step "Installing backend dependencies ..."
    try {
        & $VenvPip install -r $ReqFile --quiet
        if ($LASTEXITCODE -ne 0) { throw "pip install failed with exit code $LASTEXITCODE" }
        Write-Ok "Backend dependencies installed."
        $backendOk = $true
    } catch {
        Write-Fail "Failed to install backend dependencies: $_"
    }
}

# ── 5. Install frontend dependencies ──────────────────────────────────────────
Write-Header "5/5  Frontend Dependencies"
if (-not $nodeOk) {
    Write-Warn "Skipped — Node.js not available."
} elseif (-not (Test-Path (Join-Path $Frontend "package.json"))) {
    Write-Warn "package.json not found at $Frontend — frontend may not be scaffolded yet."
} else {
    Write-Step "Installing frontend dependencies ..."
    try {
        Push-Location $Frontend
        & npm install --silent 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
        Write-Ok "Frontend dependencies installed."
        $frontendOk = $true
    } catch {
        Write-Fail "Failed to install frontend dependencies: $_"
    } finally {
        Pop-Location
    }
}

# ══════════════════════════════════════════════════════════════════════════════
Write-Header "Setup Summary"

$statusItems = @(
    @{ Name = "Python";          Ok = $pythonOk   },
    @{ Name = "Node.js";         Ok = $nodeOk     },
    @{ Name = "Backend venv";    Ok = $venvOk     },
    @{ Name = "Backend deps";    Ok = $backendOk  },
    @{ Name = "Frontend deps";   Ok = $frontendOk }
)

$allOk = $true
foreach ($item in $statusItems) {
    if ($item.Ok) {
        Write-Ok "$($item.Name)"
    } else {
        Write-Fail "$($item.Name)"
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "  All checks passed! Start developing:" -ForegroundColor Green
    Write-Host ""
    Write-Host "    # Backend (Terminal 1)" -ForegroundColor DarkGray
    Write-Host "    cd backend" -ForegroundColor White
    Write-Host "    .venv\Scripts\activate" -ForegroundColor White
    Write-Host "    uvicorn app.main:app --reload" -ForegroundColor White
    Write-Host ""
    Write-Host "    # Frontend (Terminal 2)" -ForegroundColor DarkGray
    Write-Host "    cd frontend" -ForegroundColor White
    Write-Host "    npm run dev" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "  Some steps failed. Fix the issues above and re-run:" -ForegroundColor Yellow
    Write-Host "    .\scripts\setup.ps1" -ForegroundColor White
    Write-Host ""
}
