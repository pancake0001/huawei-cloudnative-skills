param(
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"
$skillsRoot = Join-Path $RepoRoot "skills"
$scriptsTarget = Join-Path $RepoRoot "scripts"

Get-ChildItem -Path $skillsRoot -Directory | ForEach-Object {
  $skillDir = $_.FullName
  $profile = Join-Path $skillDir "skill-profile.yaml"
  $skillMd = Join-Path $skillDir "SKILL.md"
  if (-not (Test-Path -LiteralPath $profile) -and -not (Test-Path -LiteralPath $skillMd)) {
    return
  }

  $linkPath = Join-Path $skillDir "scripts"
  if (Test-Path -LiteralPath $linkPath) {
    $item = Get-Item -LiteralPath $linkPath -Force
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -eq 0) {
      throw "$linkPath exists but is not a SymbolicLink/Junction. Refusing to overwrite."
    }
    Write-Host "exists $linkPath"
    return
  }

  try {
    New-Item -ItemType SymbolicLink -Path $linkPath -Target "..\..\scripts" | Out-Null
    Write-Host "linked $linkPath -> ..\..\scripts"
  }
  catch {
    New-Item -ItemType Junction -Path $linkPath -Target $scriptsTarget | Out-Null
    Write-Host "junction $linkPath -> $scriptsTarget"
  }
}
