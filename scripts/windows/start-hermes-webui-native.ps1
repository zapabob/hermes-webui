[CmdletBinding()]
param(
    [int]$Port = 8787,
    [string]$BindHost = "127.0.0.1",
    [switch]$Open
)

$ErrorActionPreference = "Stop"

function Get-HermesHome {
    if ($env:HERMES_HOME -and $env:HERMES_HOME.Trim()) {
        return $env:HERMES_HOME.Trim()
    }
    return (Join-Path $env:USERPROFILE ".hermes")
}

function Read-DotEnvValue {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }

    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#") -or -not $trimmed.Contains("=")) {
            continue
        }

        $parts = $trimmed -split "=", 2
        $key = ($parts[0].Trim().TrimStart([char]0xFEFF) -replace "^export\s+", "")
        if ($key -ne $Name) {
            continue
        }

        $value = $parts[1].Trim()
        if ($value -match '^"(.*)"$') {
            return $Matches[1]
        }
        if ($value -match "^'(.*)'$") {
            return $Matches[1]
        }
        return $value
    }

    return $null
}

function Resolve-WebUiPassword {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HermesHome,

        [Parameter(Mandatory = $true)]
        [string]$WebUiEnvPath
    )

    if ($env:HERMES_WEBUI_PASSWORD -and $env:HERMES_WEBUI_PASSWORD.Trim()) {
        return @{ Password = $env:HERMES_WEBUI_PASSWORD; Source = "process environment" }
    }

    if ($env:HERMES_WEBUI_PASSWORD_FILE -and $env:HERMES_WEBUI_PASSWORD_FILE.Trim()) {
        $passwordFile = $env:HERMES_WEBUI_PASSWORD_FILE.Trim()
        if (Test-Path -LiteralPath $passwordFile) {
            $password = Get-Content -LiteralPath $passwordFile -Encoding UTF8 -TotalCount 1
            if ($password -and $password.Trim()) {
                return @{ Password = $password.Trim(); Source = "HERMES_WEBUI_PASSWORD_FILE" }
            }
        } else {
            Write-Warning "HERMES_WEBUI_PASSWORD_FILE is set but was not found; falling back to env files."
        }
    }

    $hermesEnv = Join-Path $HermesHome ".env"
    $passwordFromHermesEnv = Read-DotEnvValue -Path $hermesEnv -Name "HERMES_WEBUI_PASSWORD"
    if ($passwordFromHermesEnv -and $passwordFromHermesEnv.Trim()) {
        return @{ Password = $passwordFromHermesEnv.Trim(); Source = "$HermesHome\.env" }
    }

    $legacyPassword = Read-DotEnvValue -Path $WebUiEnvPath -Name "HERMES_WEBUI_PASSWORD"
    if ($legacyPassword -and $legacyPassword.Trim()) {
        return @{ Password = $legacyPassword.Trim(); Source = "legacy WebUI .env" }
    }

    return $null
}

function Test-TruthyEnv {
    param([string]$Value)
    if (-not $Value) {
        return $false
    }
    return $Value.Trim().ToLowerInvariant() -in @("1", "true", "yes", "on")
}

function Start-WebUiBrowserOpener {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url
    )

    $encodedUrl = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($Url))
    $script = @"
`$url = [System.Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('$encodedUrl'))
for (`$i = 0; `$i -lt 60; `$i++) {
    try {
        `$response = Invoke-WebRequest -UseBasicParsing -Uri `$url -TimeoutSec 2
        if (`$response.StatusCode -ge 200 -and `$response.StatusCode -lt 500) {
            Start-Process `$url
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 1
}
Start-Process `$url
"@
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-WindowStyle",
        "Hidden",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        $script
    ) -WindowStyle Hidden | Out-Null
}

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$ProjectRoot = Resolve-Path (Join-Path $RepoRoot "..")
$AgentDir = Join-Path $ProjectRoot "hermes-agent"
$AgentPythonCandidates = @(
    (Join-Path $AgentDir ".venv\Scripts\python.exe"),
    (Join-Path $AgentDir "venv\Scripts\python.exe")
)
$AgentPython = $AgentPythonCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $AgentPython) {
    $AgentPython = $AgentPythonCandidates[0]
}
$HermesHome = Get-HermesHome
$LogDir = Join-Path $HermesHome "logs"
$WebUiEnvPath = Join-Path $RepoRoot ".env"

New-Item -ItemType Directory -Force -Path $HermesHome, $LogDir | Out-Null

$env:HERMES_WEBUI_AGENT_DIR = $AgentDir
$env:HERMES_WEBUI_PYTHON = $AgentPython
$env:HERMES_WEBUI_HOST = $BindHost
$env:HERMES_WEBUI_PORT = "$Port"
$env:HERMES_WEBUI_STATE_DIR = Join-Path $HermesHome "webui"
$env:HERMES_WEBUI_DEFAULT_WORKSPACE = $ProjectRoot
$env:HERMES_HOME = $HermesHome
$env:HERMES_CONFIG_PATH = Join-Path $HermesHome "config.yaml"
$resolvedPassword = Resolve-WebUiPassword -HermesHome $HermesHome -WebUiEnvPath $WebUiEnvPath
if ($resolvedPassword) {
    $env:HERMES_WEBUI_PASSWORD = $resolvedPassword.Password
    $env:HERMES_WEBUI_PRESERVE_ENV = "1"
    Write-Host "Injected HERMES_WEBUI_PASSWORD from $($resolvedPassword.Source)."
}

if (-not (Test-Path -LiteralPath $AgentPython)) {
    throw "Hermes agent Python not found. Checked: $($AgentPythonCandidates -join ', ')"
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$logPath = Join-Path $LogDir "webui-$stamp.log"
$url = "http://127.0.0.1:$Port/"

if ($Open -or (Test-TruthyEnv -Value $env:HERMES_WEBUI_OPEN_ON_START)) {
    Start-WebUiBrowserOpener -Url $url
}

Push-Location $RepoRoot
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $RepoRoot "start.ps1") -Port $Port -BindHost $BindHost *> $logPath
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
