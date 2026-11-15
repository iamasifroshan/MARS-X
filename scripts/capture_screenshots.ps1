$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$outDir = "E:\MARS-X\submission\screenshots"

if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
}

$targets = @(
    @{ File = "01_exploration_console.png"; Url = "http://localhost:3005/?tab=dashboard" },
    @{ File = "02_science_discovery.png"; Url = "http://localhost:3005/?tab=discovery" },
    @{ File = "03_terrain_intelligence.png"; Url = "http://localhost:3005/?tab=terrain" },
    @{ File = "04_marswalk_routing.png"; Url = "http://localhost:3005/?tab=route" },
    @{ File = "05_route_intelligence.png"; Url = "http://localhost:3005/?tab=route&mode=intelligence&autoPlan=1" },
    @{ File = "06_environmental_climatology.png"; Url = "http://localhost:3005/?tab=environmental" },
    @{ File = "07_dataset_catalogue.png"; Url = "http://localhost:3005/?tab=catalogue" }
)

foreach ($target in $targets) {
    $outFile = Join-Path $outDir $target.File
    Write-Host "Capturing $($target.File) from $($target.Url)..."
    
    # Use Chrome headless with virtual time budget to allow React and API calls to settle
    $args = @(
        "--headless=new",
        "--hide-scrollbars",
        "--window-size=1920,1080",
        "--virtual-time-budget=6000",
        "--run-all-compositor-stages-before-draw",
        "--screenshot=$outFile",
        $target.Url
    )
    
    $proc = Start-Process -FilePath $chrome -ArgumentList $args -Wait -PassThru -NoNewWindow
    if (Test-Path $outFile) {
        $size = (Get-Item $outFile).Length
        Write-Host "  Success: $outFile ($size bytes)"
    } else {
        Write-Host "  Failed to generate $outFile"
    }
}
