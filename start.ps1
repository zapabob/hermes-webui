Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$EnvPath = Join-Path $RepoRoot ".env"

if (Test-Path -LiteralPath $EnvPath) {
    Get-Content -LiteralPath $EnvPath | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }
        $parts = $line.Split("=", 2)
        $key = $parts[0].Trim()
        if ($key.StartsWith("export ")) {
            $key = $key.Substring(7).Trim()
        }
        if (-not $key) {
            return
        }
        $value = $parts[1].Trim()
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

$pythonArgs = @()
if ($env:HERMES_WEBUI_PYTHON) {
    $pythonExe = $env:HERMES_WEBUI_PYTHON
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonExe = (Get-Command python).Source
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $pythonExe = (Get-Command python3).Source
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonExe = (Get-Command py).Source
    $pythonArgs += "-3"
} else {
    Write-Error "Python 3 is required to run bootstrap.py"
    exit 1
}

& $pythonExe @pythonArgs (Join-Path $RepoRoot "bootstrap.py") --no-browser @args
exit $LASTEXITCODE
