[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RailwayArgs
)

$ErrorActionPreference = "Stop"

if (-not $RailwayArgs -or $RailwayArgs.Count -eq 0) {
    Write-Host "Usage: .\tools\railway_safe.ps1 <railway args>"
    Write-Host "Example: .\tools\railway_safe.ps1 status"
    Write-Host "Example: .\tools\railway_safe.ps1 logs -s polymarket-bot -n 80"
    exit 1
}

$proxyVars = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY"
)

$previous = @{}
foreach ($name in $proxyVars) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    Remove-Item "Env:$name" -ErrorAction SilentlyContinue
}

try {
    $railwayCommand = Get-Command "railway.cmd" -ErrorAction SilentlyContinue
    if (-not $railwayCommand) {
        $railwayCommand = Get-Command "railway" -ErrorAction SilentlyContinue
    }
    if (-not $railwayCommand) {
        throw "railway CLI not found in PATH."
    }

    if ($RailwayArgs[0] -eq "login") {
        Write-Host "Railway login: use this from an interactive user shell."
        Write-Host "Codex still needs escalated execution later if auth refresh must touch %USERPROFILE%\.railway\config.json."
    }

    & $railwayCommand.Source @RailwayArgs
    exit $LASTEXITCODE
}
finally {
    foreach ($name in $proxyVars) {
        $value = $previous[$name]
        if ([string]::IsNullOrEmpty($value)) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            Set-Item "Env:$name" -Value $value
        }
    }
}
