[CmdletBinding()]
param(
    [int]$Port = 8787,
    [string]$BindHost = "127.0.0.1"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ProjectRoot = Resolve-Path (Join-Path $RepoRoot "..")
$AgentDir = Join-Path $ProjectRoot "hermes-agent"
$AgentPython = Join-Path $AgentDir "venv\Scripts\python.exe"
$HermesHome = Join-Path $env:USERPROFILE ".hermes"
$LogDir = Join-Path $HermesHome "logs"

New-Item -ItemType Directory -Force -Path $HermesHome, $LogDir | Out-Null

$env:HERMES_WEBUI_AGENT_DIR = $AgentDir
$env:HERMES_WEBUI_PYTHON = $AgentPython
$env:HERMES_WEBUI_HOST = $BindHost
$env:HERMES_WEBUI_PORT = "$Port"
$env:HERMES_WEBUI_STATE_DIR = Join-Path $HermesHome "webui"
$env:HERMES_WEBUI_DEFAULT_WORKSPACE = $ProjectRoot
$env:HERMES_WEBUI_DEFAULT_MODEL = "gpt-5.5"
$env:HERMES_HOME = $HermesHome
$env:HERMES_CONFIG_PATH = Join-Path $HermesHome "config.yaml"

if (-not (Test-Path -LiteralPath $AgentPython)) {
    throw "Hermes agent uv venv Python not found: $AgentPython"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $LogDir "webui-$stamp.log"

Push-Location $RepoRoot
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "start.ps1") -Port $Port -BindHost $BindHost *> $logPath
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
