# Safecam AI - Database Reset & Seeding PowerShell Helper
param (
    [switch]$UsersOnly,
    [switch]$CleanMedia,
    [switch]$WithSamples,
    [switch]$Yes
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$rootDir = Split-Path -Parent $scriptDir

$pythonArgs = @("$scriptDir\reset_db.py")

if ($UsersOnly) {
    $pythonArgs += "--users-only"
}
if ($CleanMedia) {
    $pythonArgs += "--clean-media"
}
if ($WithSamples) {
    $pythonArgs += "--with-samples"
}
if ($Yes) {
    $pythonArgs += "--yes"
}

Write-Host "Running Safecam AI Database Reset..." -ForegroundColor Cyan
& python @pythonArgs
