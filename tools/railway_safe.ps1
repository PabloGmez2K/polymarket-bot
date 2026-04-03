[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RailwayArgs
)

$ErrorActionPreference = "Stop"

if (-not $RailwayArgs -or $RailwayArgs.Count -eq 0) {
    Write-Host "Usage: .\tools\railway_safe.ps1 <railway args>"
    Write-Host "Example: .\tools\railway_safe.ps1 status"
    Write-Host "Example: .\tools\railway_safe.ps1 whoami"
    Write-Host "Example: .\tools\railway_safe.ps1 logs -s polymarket-bot -n 80"
    exit 1
}

$proxyVars = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
    "git_http_proxy",
    "git_https_proxy",
    "npm_config_proxy",
    "npm_config_https_proxy",
    "npm_config_noproxy"
)

$tokenRefreshSafetyWindowSeconds = 300
$railwayCliMutexName = "Global\polymarket-bot-railway-cli"
$railwayCliMutexTimeoutMs = 60000

function Get-RailwayConfigPath {
    return Join-Path $env:USERPROFILE ".railway\config.json"
}

function Read-RailwayConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    if (-not (Test-Path $ConfigPath)) {
        return $null
    }

    return Get-Content -Raw $ConfigPath | ConvertFrom-Json
}

function Convert-UnixTime {
    param(
        [AllowNull()]
        $EpochSeconds
    )

    if ($null -eq $EpochSeconds -or [string]::IsNullOrWhiteSpace([string]$EpochSeconds)) {
        return $null
    }

    return [DateTimeOffset]::FromUnixTimeSeconds([int64]$EpochSeconds).UtcDateTime
}

function Test-RailwayConfigWritable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    if (-not (Test-Path $ConfigPath)) {
        return $false
    }

    try {
        $stream = [System.IO.File]::Open(
            $ConfigPath,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Write,
            [System.IO.FileShare]::ReadWrite
        )
        $stream.Close()
        return $true
    }
    catch {
        return $false
    }
    finally {
        if ($null -ne $stream) {
            $stream.Dispose()
        }
    }
}

function Assert-RailwayConfigWritableBeforeRefresh {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    $config = Read-RailwayConfig -ConfigPath $ConfigPath
    if ($null -eq $config -or $null -eq $config.user) {
        return
    }

    $expiresAtUtc = Convert-UnixTime $config.user.tokenExpiresAt
    if ($null -eq $expiresAtUtc) {
        return
    }

    $secondsToExpiry = ($expiresAtUtc - [DateTime]::UtcNow).TotalSeconds
    if ($secondsToExpiry -gt $tokenRefreshSafetyWindowSeconds) {
        return
    }

    if (Test-RailwayConfigWritable -ConfigPath $ConfigPath) {
        return
    }

    Write-Host "Railway auth refresh is likely needed, but this process cannot write $ConfigPath."
    Write-Host "Run the Railway command outside the sandbox or with escalated permissions so the CLI can persist refreshed OAuth tokens."
    Write-Host "If auth is already degraded, recover with:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless"
    exit 2
}

function Invoke-WithRailwayCliLock {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock
    )

    $mutex = New-Object System.Threading.Mutex($false, $railwayCliMutexName)
    $lockAcquired = $false

    try {
        try {
            $lockAcquired = $mutex.WaitOne($railwayCliMutexTimeoutMs)
        }
        catch [System.Threading.AbandonedMutexException] {
            $lockAcquired = $true
        }

        if (-not $lockAcquired) {
            Write-Host "Another Railway CLI command is still running. Retry in a moment to avoid concurrent OAuth refresh against the same config."
            exit 3
        }

        & $ScriptBlock
    }
    finally {
        if ($lockAcquired) {
            $mutex.ReleaseMutex()
        }
        $mutex.Dispose()
    }
}

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

    Assert-RailwayConfigWritableBeforeRefresh -ConfigPath (Get-RailwayConfigPath)

    if ($RailwayArgs[0] -eq "login") {
        Write-Host "Railway login: use this from an interactive user shell."
        Write-Host "If auth is stuck in a relogin loop, run:"
        Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 doctor"
        Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset"
        Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless"
        Write-Host "Codex still needs escalated execution later if auth refresh must touch %USERPROFILE%\.railway\config.json."
    }

    Invoke-WithRailwayCliLock {
        & $railwayCommand.Source @RailwayArgs
    }
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
