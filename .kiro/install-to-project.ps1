<#
.SYNOPSIS
    Install full Kiro configuration into any project.
.DESCRIPTION
    Copies steering files, skills, hooks, agents, scripts, and memory
    from this workspace's .kiro/ directory into a target project.
    Non-destructive by default — won't overwrite existing files.
    Use -Force to update all files.
.PARAMETER TargetPath
    Path to the project root. Required.
.PARAMETER Force
    Overwrite existing files (default: skip existing).
.PARAMETER Exclude
    Comma-separated list of components to skip.
    Valid: steering, skills, agents, hooks, scripts, memory, settings
.EXAMPLE
    .\.kiro\install-to-project.ps1 D:\my-project
    .\.kiro\install-to-project.ps1 D:\my-project -Force
    .\.kiro\install-to-project.ps1 D:\my-project -Exclude "agents,scripts"
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$TargetPath,

    [switch]$Force,

    [string]$Exclude = ""
)

$ErrorActionPreference = "Stop"
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceKiro = $ScriptRoot  # This script lives inside .kiro/

# Validate target
if (-not (Test-Path $TargetPath)) {
    Write-Host "ERROR: Target path '$TargetPath' does not exist." -ForegroundColor Red
    exit 1
}

$TargetKiro = Join-Path $TargetPath ".kiro"
$ExcludeList = if ($Exclude) { $Exclude -split "," | ForEach-Object { $_.Trim().ToLower() } } else { @() }

Write-Host ""
Write-Host "  Kiro Config Installer" -ForegroundColor Cyan
Write-Host "  =====================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Source:  $SourceKiro" -ForegroundColor Gray
Write-Host "  Target:  $TargetKiro" -ForegroundColor Gray
Write-Host "  Mode:    $(if ($Force) { 'FORCE (overwrite)' } else { 'Safe (skip existing)' })" -ForegroundColor $(if ($Force) { "Yellow" } else { "Green" })
if ($ExcludeList.Count -gt 0) {
    Write-Host "  Exclude: $($ExcludeList -join ', ')" -ForegroundColor Yellow
}
Write-Host ""

# Components to copy
$components = @(
    @{ Name = "steering";  Source = "steering";  Recurse = $false; Desc = "Steering files (methodology, patterns, design quality)" },
    @{ Name = "skills";    Source = "skills";    Recurse = $true;  Desc = "Skills (19 specialized skill sets)" },
    @{ Name = "agents";    Source = "agents";    Recurse = $false; Desc = "Agent definitions (code-reviewer, planner, tdd-guide, etc.)" },
    @{ Name = "hooks";     Source = "hooks";     Recurse = $false; Desc = "Hooks (code review, design quality, session observations)" },
    @{ Name = "scripts";   Source = "scripts";   Recurse = $false; Desc = "Scripts (quality gate, formatting)" },
    @{ Name = "memory";    Source = "memory";    Recurse = $false; Desc = "Memory directory (session observation log)" },
    @{ Name = "settings";  Source = "settings";  Recurse = $false; Desc = "Settings (MCP config examples)" }
)

$totalCopied = 0
$totalSkipped = 0
$totalComponents = 0

foreach ($comp in $components) {
    # Check exclusion
    if ($ExcludeList -contains $comp.Name.ToLower()) {
        Write-Host "  SKIP $($comp.Name) (excluded)" -ForegroundColor Yellow
        continue
    }

    $srcDir = Join-Path $SourceKiro $comp.Source
    $dstDir = Join-Path $TargetKiro $comp.Name

    if (-not (Test-Path $srcDir)) {
        Write-Host "  SKIP $($comp.Name) (source not found)" -ForegroundColor Yellow
        continue
    }

    # Create target directory
    if (-not (Test-Path $dstDir)) {
        New-Item -ItemType Directory -Path $dstDir -Force | Out-Null
    }

    # Get files to copy
    $getParams = @{ Path = $srcDir; File = $true }
    if ($comp.Recurse) {
        $getParams.Recurse = $true
    }
    $files = Get-ChildItem @getParams

    $compCopied = 0
    $compSkipped = 0

    foreach ($file in $files) {
        # Calculate relative path for recursive copies
        $relativePath = $file.FullName.Substring($srcDir.Length + 1)
        $targetFile = Join-Path $dstDir $relativePath
        $targetDir = Split-Path -Parent $targetFile

        # Ensure parent directory exists
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }

        # Non-destructive: skip if target exists (unless -Force)
        if ((Test-Path $targetFile) -and -not $Force) {
            $compSkipped++
            $totalSkipped++
            continue
        }

        Copy-Item -Path $file.FullName -Destination $targetFile -Force
        $compCopied++
        $totalCopied++
    }

    $totalComponents++
    $status = if ($compCopied -gt 0) { "Green" } else { "DarkGray" }
    Write-Host "  OK $($comp.Name) ($compCopied copied, $compSkipped skipped)" -ForegroundColor $status
}

# Add .kiro/memory/ to target's .gitignore
$gitignorePath = Join-Path $TargetPath ".gitignore"
$memoryIgnore = ".kiro/memory/"
if (Test-Path $gitignorePath) {
    $gitContent = Get-Content $gitignorePath -Raw
    if ($gitContent -notmatch [regex]::Escape($memoryIgnore)) {
        Add-Content -Path $gitignorePath -Value "`n# Session memory (auto-generated, not for version control)`n$memoryIgnore"
        Write-Host "  OK .gitignore (added .kiro/memory/ entry)" -ForegroundColor Green
    } else {
        Write-Host "  OK .gitignore (already has memory entry)" -ForegroundColor DarkGray
    }
} else {
    # Create .gitignore with memory entry
    Set-Content -Path $gitignorePath -Value "# Session memory (auto-generated, not for version control)`n$memoryIgnore`n"
    Write-Host "  OK .gitignore (created with memory entry)" -ForegroundColor Green
}

Write-Host ""
Write-Host "  Done! $totalComponents components, $totalCopied files copied, $totalSkipped skipped." -ForegroundColor Cyan
Write-Host ""
Write-Host "  What's included:" -ForegroundColor White
Write-Host "    Superpowers   — brainstorming-first workflow, systematic debugging" -ForegroundColor Gray
Write-Host "    Impeccable    — design quality standards, anti-slop rules" -ForegroundColor Gray
Write-Host "    Claude-Mem    — session memory and observation logging" -ForegroundColor Gray
Write-Host "    Task Observer — meta-observation and pattern improvement" -ForegroundColor Gray
Write-Host "    + 19 skills, 15 hooks, 16 agents, quality gate scripts" -ForegroundColor Gray
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "    1. Edit .kiro/steering/lessons-learned.md with project-specific patterns"
Write-Host "    2. Edit .kiro/steering/project-context.md with your project details"
Write-Host "    3. MCP setup: Command Palette > 'MCP' if needed"
Write-Host "    4. Toggle hooks in the Agent Hooks panel"
Write-Host ""
