[CmdletBinding()]
param(
    [switch]$PrintEnvSummary,

    [string]$Executable,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Executable)) {
    Write-Host "Usage: .\tools\run_clean_network.ps1 [-PrintEnvSummary] -Executable <command> [args...]"
    Write-Host "Example: .\tools\run_clean_network.ps1 -Executable python -c ""import urllib.request; print(urllib.request.urlopen('https://data-api.polymarket.com/trades?limit=1').status)"""
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

$codexVars = @(
    "CODEX_SANDBOX_NETWORK_DISABLED",
    "CODEX_INTERNAL_ORIGINATOR_OVERRIDE",
    "CODEX_THREAD_ID"
)

$sandboxPathPatterns = @(
    "\\\.sbx-denybin($|\\)",
    "\\\.codex\\tmp\\arg0\\",
    "\\\.vscode\\extensions\\openai\.chatgpt-[^\\]+\\bin\\"
)

function Test-IsSandboxPath {
    param(
        [AllowNull()]
        [string]$Entry
    )

    if ([string]::IsNullOrWhiteSpace($Entry)) {
        return $false
    }

    foreach ($pattern in $sandboxPathPatterns) {
        if ($Entry -match $pattern) {
            return $true
        }
    }

    return $false
}

function Get-ScrubbedPathEntries {
    $entries = @()

    foreach ($entry in ($env:PATH -split ';')) {
        if ([string]::IsNullOrWhiteSpace($entry)) {
            continue
        }

        if (Test-IsSandboxPath -Entry $entry) {
            continue
        }

        if (-not ($entries -icontains $entry)) {
            $entries += $entry
        }
    }

    return $entries
}

function Get-CurrentProxySnapshot {
    $snapshot = @{}
    foreach ($name in ($proxyVars + $codexVars)) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $snapshot[$name] = $value
        }
    }

    return $snapshot
}

$previous = @{}
foreach ($name in ($proxyVars + $codexVars)) {
    $previous[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}
$previous["PATH"] = $env:PATH

try {
    foreach ($name in $proxyVars) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }

    foreach ($name in $codexVars) {
        Remove-Item "Env:$name" -ErrorAction SilentlyContinue
    }

    $cleanPathEntries = Get-ScrubbedPathEntries
    $env:PATH = ($cleanPathEntries -join ';')

    if ($PrintEnvSummary) {
        Write-Host "Removed proxy/codex vars:"
        foreach ($name in ($proxyVars + $codexVars)) {
            if (-not [string]::IsNullOrWhiteSpace($previous[$name])) {
                Write-Host ("  {0}={1}" -f $name, $previous[$name])
            }
        }

        Write-Host "PATH entries removed:"
        foreach ($entry in ($previous["PATH"] -split ';')) {
            if (Test-IsSandboxPath -Entry $entry) {
                Write-Host "  $entry"
            }
        }

        Write-Host "Effective PATH:"
        foreach ($entry in $cleanPathEntries) {
            Write-Host "  $entry"
        }
    }

    & $Executable @Arguments
    exit $LASTEXITCODE
}
finally {
    foreach ($name in ($proxyVars + $codexVars)) {
        $value = $previous[$name]
        if ([string]::IsNullOrWhiteSpace($value)) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
        else {
            Set-Item "Env:$name" -Value $value
        }
    }

    $env:PATH = $previous["PATH"]
}
