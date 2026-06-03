$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = if ($env:PROJECT_DIR) { $env:PROJECT_DIR } else { Split-Path -Parent $ScriptDir }
$ComposeFile = if ($env:COMPOSE_FILE) { $env:COMPOSE_FILE } else { "compose.yaml" }

Set-Location $ProjectDir

$EnvFile = Join-Path $ProjectDir ".env"
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
        $parts = $line.Split("=", 2)
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

if (-not $env:DRINK_POS_IMAGE) {
    $env:DRINK_POS_IMAGE = "ghcr.io/tostman1/drink-pos:latest"
}

podman pull --policy newer $env:DRINK_POS_IMAGE

$composeOk = $false
try {
    podman compose version | Out-Null
    $composeOk = $true
} catch {
    $composeOk = $false
}

if ($composeOk) {
    podman compose -f $ComposeFile up -d --remove-orphans --force-recreate
} elseif (Get-Command podman-compose -ErrorAction SilentlyContinue) {
    podman-compose -f $ComposeFile up -d --force-recreate
} else {
    throw "podman compose or podman-compose is required."
}

podman image prune -f
