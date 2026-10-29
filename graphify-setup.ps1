#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Bootstrap Graphify for any project. Run from the project root:
    powershell -ExecutionPolicy Bypass -File "d:\kiro\graphify-setup.ps1" [optional-target-dir]
    
.DESCRIPTION
    - Installs the Graphify Kiro skill + steering into the target project
    - Builds the knowledge graph (code-only, no LLM needed)
    - Adds graphify-out/ to .gitignore if not already there
#>

param(
    [string]$TargetDir = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
$env:Path = "C:\Users\vikas sharma\.local\bin;$env:Path"

Write-Host "`n=== Graphify Setup for Kiro ===" -ForegroundColor Cyan
Write-Host "Target: $TargetDir`n"

# 1. Check graphify is available
if (-not (Get-Command graphify -ErrorAction SilentlyContinue)) {
    Write-Host "[!] graphify not found. Installing..." -ForegroundColor Yellow
    $env:UV_HTTP_TIMEOUT = "600"
    uv tool install graphifyy --python 3.12
}

# 2. Install Kiro integration (project-scoped)
Write-Host "[1/3] Installing Kiro skill + steering..." -ForegroundColor Green
Push-Location $TargetDir
try {
    graphify kiro install --project
} finally {
    Pop-Location
}

# 3. Build the knowledge graph
Write-Host "[2/3] Building knowledge graph (code-only, local AST)..." -ForegroundColor Green
$env:GRAPHIFY_BACKEND = "none"
Push-Location $TargetDir
try {
    graphify extract . --code-only
    graphify cluster-only .
} finally {
    Pop-Location
}

# 4. Add graphify-out/ to .gitignore
$gitignorePath = Join-Path $TargetDir ".gitignore"
if (Test-Path $gitignorePath) {
    $content = Get-Content $gitignorePath -Raw
    if ($content -notmatch "graphify-out") {
        Write-Host "[3/3] Adding graphify-out/ to .gitignore..." -ForegroundColor Green
        Add-Content $gitignorePath "`n# Graphify knowledge graph (rebuild with: graphify extract . --code-only)`ngraphify-out/"
    } else {
        Write-Host "[3/3] graphify-out/ already in .gitignore" -ForegroundColor DarkGray
    }
} else {
    Write-Host "[3/3] Creating .gitignore with graphify-out/..." -ForegroundColor Green
    Set-Content $gitignorePath "# Graphify knowledge graph (rebuild with: graphify extract . --code-only)`ngraphify-out/"
}

Write-Host "`n=== Done! ===" -ForegroundColor Cyan
Write-Host "  Graph:  $TargetDir\graphify-out\graph.json"
Write-Host "  Visual: $TargetDir\graphify-out\graph.html (open in browser)"
Write-Host "  Report: $TargetDir\graphify-out\GRAPH_REPORT.md"
Write-Host "`nKiro will now query the graph automatically for codebase questions.`n"
