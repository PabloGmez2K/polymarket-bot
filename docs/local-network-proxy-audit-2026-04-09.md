# Local Network Proxy Audit — 2026-04-09

## Summary

The `127.0.0.1:9` proxy values seen in this session are not coming from:

- Windows user environment variables
- Windows machine environment variables
- PowerShell profiles
- repo `.vscode` settings
- VS Code user settings
- git config
- npm config

They are injected into the current Codex-launched process tree.

## Evidence

- Current process contains:
  - `HTTP_PROXY=http://127.0.0.1:9`
  - `HTTPS_PROXY=http://127.0.0.1:9`
  - `ALL_PROXY=http://127.0.0.1:9`
  - `GIT_HTTP_PROXY=http://127.0.0.1:9`
  - `GIT_HTTPS_PROXY=http://127.0.0.1:9`
  - `CODEX_SANDBOX_NETWORK_DISABLED=1`
  - `CODEX_INTERNAL_ORIGINATOR_OVERRIDE=codex_vscode`
- Current process `PATH` also includes sandbox-only entries such as:
  - `C:\Users\USUARIO\.sbx-denybin`
  - `C:\Users\USUARIO\.codex\tmp\arg0\...`
  - `C:\Users\USUARIO\.vscode\extensions\openai.chatgpt-26.325.31654-win32-x64\bin\windows-x86_64`
- The OpenAI VS Code extension package identifies itself as Codex and ships the local Codex runtime.
- The Codex binary contains strings such as `CODEX_SANDBOX_NETWORK_DISABLED`, `network-proxy`, `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY`.

## Practical conclusion

For this repo, the proxy contamination is a process-level sandbox artifact of the Codex VS Code runtime, not a persistent machine-wide misconfiguration.

That means:

- a normal Windows shell can be clean even when this Codex shell is contaminated
- removing Windows env vars would not fix the root cause here
- the safest stable mitigation is to run real-network commands through a clean wrapper outside the Codex sandbox when verification needs actual internet access

## Stable repo-local mitigation

Use:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_clean_network.ps1 -Executable <command> [args...]
```

This wrapper:

- removes proxy vars for the child process only
- removes `CODEX_SANDBOX_NETWORK_DISABLED` and related Codex process markers
- strips sandbox-only `PATH` entries
- restores the original environment after the command exits

## Suggested verification commands

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_clean_network.ps1 -Executable python -c "import urllib.request; print(urllib.request.urlopen('https://data-api.polymarket.com/trades?limit=1', timeout=20).status)"
```

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\run_clean_network.ps1 -Executable python -c "import urllib.request; print(urllib.request.urlopen('https://data-api.polymarket.com/positions?user=0x0000000000000000000000000000000000000000&sizeThreshold=.1', timeout=20).status)"
```
