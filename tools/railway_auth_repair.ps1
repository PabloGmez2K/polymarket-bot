[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [ValidateSet("doctor", "backup", "reset", "restore-links", "launch-login", "interactive-login")]
    [string]$Action = "doctor",

    [switch]$Browserless,

    [string]$BackupPath
)

$ErrorActionPreference = "Stop"

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

$repoRoot = Split-Path $PSScriptRoot -Parent
$tokenRefreshSafetyWindowSeconds = 300
$railwayCliMutexName = "Global\polymarket-bot-railway-cli"
$railwayCliMutexTimeoutMs = 60000

function Get-RailwayCommand {
    $railwayCommand = Get-Command "railway.cmd" -ErrorAction SilentlyContinue
    if (-not $railwayCommand) {
        $railwayCommand = Get-Command "railway" -ErrorAction SilentlyContinue
    }
    if (-not $railwayCommand) {
        throw "railway CLI not found in PATH."
    }

    return $railwayCommand
}

function Invoke-InCleanRailwayEnv {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$ScriptBlock
    )

    $previous = @{}
    foreach ($name in $proxyVars) {
        $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }

    try {
        & $ScriptBlock
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
}

function Get-RailwayConfigPath {
    return Join-Path $env:USERPROFILE ".railway\config.json"
}

function Read-RailwayConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    if (-not (Test-Path $ConfigPath)) {
        throw "Railway config not found at $ConfigPath"
    }

    return Get-Content -Raw $ConfigPath | ConvertFrom-Json
}

function Get-LatestRailwayBackupPath {
    $backup = Get-ChildItem (Join-Path $env:USERPROFILE ".railway\config.backup.*.json") -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -eq $backup) {
        throw "No Railway config backup found in $env:USERPROFILE\.railway"
    }

    return $backup.FullName
}

function Set-NoteProperty {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Object,

        [Parameter(Mandatory = $true)]
        [string]$Name,

        [AllowNull()]
        $Value
    )

    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
    else {
        $Object.$Name = $Value
    }
}

function Get-ProjectLinkCount {
    param(
        [AllowNull()]
        [object]$Projects
    )

    if ($null -eq $Projects) {
        return 0
    }

    return @($Projects.PSObject.Properties).Count
}

function Get-BackupPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $directory = Split-Path $ConfigPath
    return Join-Path $directory "config.backup.$timestamp.json"
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
            throw "Another Railway CLI command is still running. Retry in a moment to avoid concurrent OAuth refresh against the same config."
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

function Backup-RailwayConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ConfigPath
    )

    $backupPath = Get-BackupPath -ConfigPath $ConfigPath
    if ($script:PSCmdlet.ShouldProcess($ConfigPath, "Create backup at $backupPath")) {
        Copy-Item -LiteralPath $ConfigPath -Destination $backupPath -Force
        Write-Host "Backup created: $backupPath"
    }

    return $backupPath
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,

        [Parameter(Mandatory = $true)]
        [string]$Content
    )

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8NoBom)
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

function Get-ProxySnapshot {
    $expected = @{}
    foreach ($name in $proxyVars) {
        $expected[$name.ToUpperInvariant()] = $true
    }

    $items = foreach ($item in Get-ChildItem Env:) {
        if ($expected.ContainsKey($item.Name.ToUpperInvariant())) {
            [pscustomobject]@{
                Name = $item.Name
                Value = $item.Value
            }
        }
    }

    return @($items)
}

function Get-PersistentProxySnapshot {
    $items = @()
    foreach ($scope in @("User", "Machine")) {
        $variables = [Environment]::GetEnvironmentVariables($scope)
        foreach ($key in $variables.Keys) {
            $name = [string]$key
            if ($proxyVars -icontains $name) {
                $value = $variables[$key]
                $items += [pscustomobject]@{
                    Scope = $scope
                    Name = $name
                    Value = $value
                }
            }
        }
    }

    return $items
}

function Invoke-RailwayCapture {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$RailwayArgs
    )

    $railwayCommand = Get-RailwayCommand
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"

    try {
        $output = Invoke-WithRailwayCliLock {
            Invoke-InCleanRailwayEnv { & $railwayCommand.Source @RailwayArgs 2>&1 }
        }
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }

    $normalizedOutput = foreach ($line in @($output)) {
        if ($line -is [System.Management.Automation.ErrorRecord]) {
            $line.Exception.Message
        }
        else {
            [string]$line
        }
    }

    return [pscustomobject]@{
        ExitCode = $exitCode
        Output = @($normalizedOutput)
    }
}

function Show-Doctor {
    $configPath = Get-RailwayConfigPath
    $railwayCommand = Get-RailwayCommand
    $processProxies = Get-ProxySnapshot
    $persistentProxies = Get-PersistentProxySnapshot

    Write-Host "Railway CLI"
    Write-Host "  Path: $($railwayCommand.Source)"
    $version = Invoke-WithRailwayCliLock { & $railwayCommand.Source --version }
    Write-Host "  Version: $version"
    Write-Host ""

    Write-Host "Proxy vars in current process"
    if ($processProxies.Count -eq 0) {
        Write-Host "  (none)"
    }
    else {
        foreach ($item in $processProxies) {
            Write-Host "  $($item.Name)=$($item.Value)"
        }
    }
    Write-Host ""

    Write-Host "Persistent proxy vars in Windows env"
    if ($persistentProxies.Count -eq 0) {
        Write-Host "  (none)"
    }
    else {
        foreach ($item in $persistentProxies) {
            Write-Host "  [$($item.Scope)] $($item.Name)=$($item.Value)"
        }
    }
    Write-Host ""

    if (Test-Path $configPath) {
        $configItem = Get-Item $configPath
        $config = Read-RailwayConfig -ConfigPath $configPath
        $user = $config.user
        $expiresAtUtc = $null
        $hasAccessToken = $false
        $hasRefreshToken = $false

        if ($null -ne $user) {
            $expiresAtUtc = Convert-UnixTime $user.tokenExpiresAt
            $hasAccessToken = $null -ne $user.accessToken
            $hasRefreshToken = $null -ne $user.refreshToken
        }

        Write-Host "Railway config"
        Write-Host "  Path: $configPath"
        Write-Host "  LastWriteTimeUtc: $($configItem.LastWriteTimeUtc.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
        Write-Host "  Linked projects: $(Get-ProjectLinkCount $config.projects)"
        Write-Host "  Writable from this process: $(Test-RailwayConfigWritable -ConfigPath $configPath)"
        Write-Host "  accessToken present: $hasAccessToken"
        Write-Host "  refreshToken present: $hasRefreshToken"
        if ($null -ne $expiresAtUtc) {
            Write-Host "  tokenExpiresAtUtc: $($expiresAtUtc.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
            $secondsToExpiry = [int][Math]::Round(($expiresAtUtc - [DateTime]::UtcNow).TotalSeconds)
            Write-Host "  secondsToExpiry: $secondsToExpiry"
            Write-Host "  refreshWriteRiskSoon: $($secondsToExpiry -le $tokenRefreshSafetyWindowSeconds)"
        }
        else {
            Write-Host "  tokenExpiresAtUtc: (null)"
            Write-Host "  secondsToExpiry: (null)"
            Write-Host "  refreshWriteRiskSoon: False"
        }
    }
    else {
        Write-Host "Railway config"
        Write-Host "  Missing: $configPath"
    }
    Write-Host ""

    $authCheck = Invoke-RailwayCapture -RailwayArgs @("whoami")
    Write-Host "Auth check via clean env"
    foreach ($line in $authCheck.Output) {
        if (-not [string]::IsNullOrWhiteSpace([string]$line)) {
            Write-Host "  $line"
        }
    }
    Write-Host "  ExitCode: $($authCheck.ExitCode)"
    Write-Host ""

    if ($authCheck.ExitCode -ne 0) {
        Write-Host "Recommended recovery"
        Write-Host "  1. powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 reset"
        Write-Host "  2. powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless"
        Write-Host "  3. powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami"
        Write-Host "  4. powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status"
    }
}

function Reset-RailwayAuth {
    $configPath = Get-RailwayConfigPath
    $config = Read-RailwayConfig -ConfigPath $configPath
    $backupPath = Backup-RailwayConfig -ConfigPath $configPath

    if ($null -eq $config.user) {
        $config | Add-Member -NotePropertyName user -NotePropertyValue ([pscustomobject]@{})
    }

    Set-NoteProperty -Object $config.user -Name "token" -Value $null
    Set-NoteProperty -Object $config.user -Name "accessToken" -Value $null
    Set-NoteProperty -Object $config.user -Name "refreshToken" -Value $null
    Set-NoteProperty -Object $config.user -Name "tokenExpiresAt" -Value $null

    $json = $config | ConvertTo-Json -Depth 10
    if ($script:PSCmdlet.ShouldProcess($configPath, "Clear stale Railway auth tokens while preserving project links")) {
        Write-Utf8NoBom -Path $configPath -Content $json
        Write-Host "Railway auth tokens cleared in $configPath"
        Write-Host "Project links preserved: $(Get-ProjectLinkCount $config.projects)"
        Write-Host "Backup available at: $backupPath"
        Write-Host "Next step: powershell -ExecutionPolicy Bypass -File .\tools\railway_auth_repair.ps1 launch-login -Browserless"
    }
}

function Restore-RailwayProjectLinks {
    $configPath = Get-RailwayConfigPath
    $sourceBackupPath = $BackupPath
    if ([string]::IsNullOrWhiteSpace($sourceBackupPath)) {
        $sourceBackupPath = Get-LatestRailwayBackupPath
    }

    $currentConfig = Read-RailwayConfig -ConfigPath $configPath
    $backupConfig = Read-RailwayConfig -ConfigPath $sourceBackupPath

    Set-NoteProperty -Object $currentConfig -Name "projects" -Value $backupConfig.projects

    $json = $currentConfig | ConvertTo-Json -Depth 10
    if ($script:PSCmdlet.ShouldProcess($configPath, "Restore Railway project links from $sourceBackupPath")) {
        Write-Utf8NoBom -Path $configPath -Content $json
        Write-Host "Railway project links restored from $sourceBackupPath"
        Write-Host "Linked projects restored: $(Get-ProjectLinkCount $currentConfig.projects)"
        Write-Host "Validation:"
        Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status"
    }
}

function Launch-CleanLoginShell {
    $powershellExe = (Get-Command "powershell.exe").Source
    $startArgs = @(
        "-NoExit",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        $PSCommandPath,
        "interactive-login"
    )

    if ($Browserless) {
        $startArgs += "-Browserless"
    }

    if ($script:PSCmdlet.ShouldProcess($powershellExe, "Open a clean Railway login shell")) {
        Start-Process -FilePath $powershellExe -ArgumentList $startArgs | Out-Null
        Write-Host "Opened a clean PowerShell window for Railway login."
    }
}

function Start-InteractiveLogin {
    $railwayCommand = Get-RailwayCommand
    Set-Location $repoRoot

    Write-Host "Clean Railway login shell"
    Write-Host "  Working directory: $repoRoot"
    Write-Host "  Proxy vars are scrubbed only for this shell."
    Write-Host ""

    $loginArgs = @("login")
    if ($Browserless) {
        $loginArgs += "--browserless"
    }

    Invoke-WithRailwayCliLock {
        Invoke-InCleanRailwayEnv {
            & $railwayCommand.Source @loginArgs
        }
    }

    Write-Host ""
    Write-Host "Validation commands"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 whoami"
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\tools\railway_safe.ps1 status"
}

switch ($Action) {
    "doctor" { Show-Doctor }
    "backup" {
        $configPath = Get-RailwayConfigPath
        Backup-RailwayConfig -ConfigPath $configPath | Out-Null
    }
    "reset" { Reset-RailwayAuth }
    "restore-links" { Restore-RailwayProjectLinks }
    "launch-login" { Launch-CleanLoginShell }
    "interactive-login" { Start-InteractiveLogin }
}
