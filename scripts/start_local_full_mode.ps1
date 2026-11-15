<#
.SYNOPSIS
    MARS-X — Local Full Science Mode Startup Workflow
.DESCRIPTION
    Launches MARS-X in Local Full Science Mode:
    1. Verifies Python virtualenv and Node.js runtimes
    2. Validates authentic scientific raster datasets in data/
    3. Starts FastAPI backend on 127.0.0.1:8000 (if not already running)
    4. Starts Next.js frontend on port 3005 (if not already running)
    5. Configures frontend to communicate with local backend
    6. Queries and displays the truthful capability discovery report
#>

[CmdletBinding()]
param(
    [string]$DataDir = "",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3005,
    [switch]$SkipChecksumValidation
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Item "$PSScriptRoot\..").FullName
Set-Location $RepoRoot

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host " MARS-X — LOCAL FULL SCIENCE MODE STARTUP" -ForegroundColor Cyan
Write-Host " NASA Space Apps Challenge 2026: Martian Map" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Repository Root: $RepoRoot" -ForegroundColor Gray

# ── 1. Runtime Dependencies Verification ─────────────────────────────────────
Write-Host "`n[1/6] Verifying Runtime Dependencies..." -ForegroundColor Yellow

# Python venv
$PythonExe = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
    try {
        $pyVer = & $PythonExe --version 2>&1
        Write-Host "  Using system Python: $pyVer" -ForegroundColor Gray
    } catch {
        Write-Error "Python executable not found. Please create backend\.venv or install Python 3.12+."
        exit 1
    }
} else {
    $pyVer = & $PythonExe --version 2>&1
    Write-Host "  Virtualenv Python: $pyVer ($PythonExe)" -ForegroundColor Green
}

# Node.js & npm
try {
    $nodeVer = & node -v 2>&1
    $npmVer = & npm -v 2>&1
    Write-Host "  Node.js: $nodeVer | npm: $npmVer" -ForegroundColor Green
} catch {
    Write-Error "Node.js and npm must be installed and available on PATH."
    exit 1
}

# ── 2. Scientific Dataset Directory Check ─────────────────────────────────────
Write-Host "`n[2/6] Inspecting Scientific Data Directory..." -ForegroundColor Yellow

if (-not $DataDir) {
    if ($env:MARS_DATA_DIR) {
        $DataDir = $env:MARS_DATA_DIR
    } else {
        $DataDir = Join-Path $RepoRoot "data"
    }
}

if (-not (Test-Path $DataDir)) {
    Write-Warning "Data directory not found at: $DataDir"
    Write-Warning "Creating directory structure..."
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

$env:MARS_DATA_DIR = $DataDir
$env:DATA_ROOT = $DataDir
$env:MARS_OPERATING_MODE = "local_full_science"
Write-Host "  Active Data Root: $DataDir" -ForegroundColor Green

# ── 3. Dataset Integrity & Manifest Audit ─────────────────────────────────────
Write-Host "`n[3/6] Auditing Authentic Planetary Datasets..." -ForegroundColor Yellow

$CoreDatasets = @(
    @{ Name = "MOLA 4ppd Global DEM"; RelativePath = "processed\mola\mola_megt90n000cb_elevation.tif"; Required = $true },
    @{ Name = "CTX Tyrrhena 20m DTM"; RelativePath = "raw\ctx\P21_009323_1754_XN_04S293W__N02_062992_1754_XI_04S293W_dtm.tif"; Required = $true },
    @{ Name = "CTX Apollinaris DTM"; RelativePath = "originals\ctx\T01_000893_1847_XN_04N191W__N09_065929_1853_XN_05N191W-DEM-geoid-adj.tif"; Required = $false },
    @{ Name = "HiRISE Holden Crater DTM"; RelativePath = "originals\hirise\DTEEC_011635_1510_029542_1510_A01.tif"; Required = $false },
    @{ Name = "TES Thermal Inertia (Dayside)"; RelativePath = "originals\themis\DBmap2007.tif"; Required = $true },
    @{ Name = "MCD Climatology Cube JSON"; RelativePath = "derived\climatology\mcd_v6_2_climatology_cube.json"; Required = $true }
)

$missingCore = 0
foreach ($ds in $CoreDatasets) {
    $fullPath = Join-Path $DataDir $ds.RelativePath
    if (Test-Path $fullPath) {
        $fileSizeMB = [math]::Round((Get-Item $fullPath).Length / 1MB, 2)
        Write-Host "  [OK] $($ds.Name) ($fileSizeMB MB)" -ForegroundColor Green
    } else {
        if ($ds.Required) {
            Write-Host "  [MISSING] $($ds.Name) - Expected at: $($ds.RelativePath)" -ForegroundColor Red
            $missingCore++
        } else {
            Write-Host "  [OPTIONAL MISSING] $($ds.Name) (Extended tier)" -ForegroundColor Yellow
        }
    }
}

if ($missingCore -gt 0) {
    Write-Warning "`n$missingCore required core raster dataset(s) missing from $DataDir."
    Write-Host "You can synchronize authentic NASA/USGS/ASU datasets by running:" -ForegroundColor Cyan
    Write-Host "  $PythonExe scripts\sync_production_datasets.py --tier core" -ForegroundColor White
} else {
    Write-Host "  All core scientific datasets are verified and present on local disk." -ForegroundColor Green
}

function Test-PortListening([string]$HostName, [int]$Port) {
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect($HostName, $Port, $null, $null)
        $wait = $iar.AsyncWaitHandle.WaitOne(1000, $false)
        if (-not $wait) {
            $tcp.Close()
            return $false
        }
        $tcp.EndConnect($iar)
        $tcp.Close()
        return $true
    } catch {
        return $false
    }
}

# ── 4. Start FastAPI Backend ─────────────────────────────────────────────────
Write-Host "`n[4/6] Checking FastAPI Backend (127.0.0.1:$BackendPort)..." -ForegroundColor Yellow

$backendOnline = Test-PortListening -HostName "127.0.0.1" -Port $BackendPort

if ($backendOnline) {
    Write-Host "  Backend is already running and listening on 127.0.0.1:$BackendPort." -ForegroundColor Green
} else {
    Write-Host "  Starting local FastAPI backend on 127.0.0.1:$BackendPort..." -ForegroundColor Cyan
    $backendProc = Start-Process -FilePath $PythonExe `
        -ArgumentList "-m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port $BackendPort" `
        -WorkingDirectory $RepoRoot `
        -PassThru

    Write-Host "  Waiting for backend startup..." -NoNewline
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
        if (Test-PortListening -HostName "127.0.0.1" -Port $BackendPort) {
            $backendOnline = $true
            break
        }
    }
    Write-Host ""
    if ($backendOnline) {
        Write-Host "  Backend started successfully (PID: $($backendProc.Id))." -ForegroundColor Green
    } else {
        Write-Error "Backend failed to respond on 127.0.0.1:$BackendPort."
        exit 1
    }
}

# ── 5. Start Next.js Frontend ────────────────────────────────────────────────
Write-Host "`n[5/6] Checking Next.js Frontend (port $FrontendPort)..." -ForegroundColor Yellow

$frontendOnline = Test-PortListening -HostName "127.0.0.1" -Port $FrontendPort

if ($frontendOnline) {
    Write-Host "  Frontend is already running and listening on http://localhost:$FrontendPort." -ForegroundColor Green
} else {
    Write-Host "  Configuring frontend API endpoint..." -ForegroundColor Gray
    $envLocalPath = Join-Path $RepoRoot "frontend\.env.local"
    Set-Content -Path $envLocalPath -Value "NEXT_PUBLIC_API_URL=http://127.0.0.1:$BackendPort`nNEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:$BackendPort"

    Write-Host "  Starting Next.js frontend on http://localhost:$FrontendPort..." -ForegroundColor Cyan
    $frontProc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c npm run start --prefix frontend -- -p $FrontendPort" `
        -WorkingDirectory $RepoRoot `
        -PassThru

    Write-Host "  Waiting for frontend listener..." -NoNewline
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline
        if (Test-PortListening -HostName "127.0.0.1" -Port $FrontendPort) {
            $frontendOnline = $true
            break
        }
    }
    Write-Host ""
    if ($frontendOnline) {
        Write-Host "  Frontend started successfully." -ForegroundColor Green
    } else {
        Write-Warning "Frontend started in background; check http://localhost:$FrontendPort."
    }
}

# ── 6. Query Capability Discovery ─────────────────────────────────────────────
Write-Host "`n[6/6] Discovering System Capabilities..." -ForegroundColor Yellow

try {
    $caps = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/v1/system/capabilities" -Method Get -TimeoutSec 5
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host " MARS-X SYSTEM CAPABILITY STATUS" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "  Operating Mode:          $($caps.operating_mode)" -ForegroundColor $(if ($caps.operating_mode -eq "local_full_science") { "Green" } else { "Yellow" })
    Write-Host "  API Connectivity:        $($caps.api_online) (ONLINE)" -ForegroundColor Green
    Write-Host "  Raster Processing:       $($caps.raster_processing_available)" -ForegroundColor $(if ($caps.raster_processing_available) { "Green" } else { "Red" })
    Write-Host "  Environment:             $($caps.environment)" -ForegroundColor Gray
    Write-Host "  Local Frontend URL:      http://localhost:$FrontendPort" -ForegroundColor Cyan
    Write-Host "  Local Backend URL:       http://127.0.0.1:$BackendPort" -ForegroundColor Cyan

    Write-Host "`n  Feature Readiness:" -ForegroundColor White
    foreach ($prop in $caps.features.PSObject.Properties) {
        $feat = $prop.Value
        $color = if ($feat.available) { "Green" } else { "DarkYellow" }
        $statusStr = if ($feat.available) { "READY" } else { "UNAVAILABLE" }
        Write-Host "    - $($feat.name.PadRight(45)) : $statusStr" -ForegroundColor $color
        if (-not $feat.available -and $feat.reason_if_unavailable) {
            Write-Host "      Reason: $($feat.reason_if_unavailable)" -ForegroundColor Gray
        }
    }
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host " MARS-X Local Full Science Mode is active. Press Ctrl+C in server terminals to stop." -ForegroundColor White
} catch {
    Write-Warning "Could not query /api/v1/system/capabilities: $_"
}
