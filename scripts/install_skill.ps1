# AIエージェントの custom-skills / Antigravity skills へ SKILL.md を配置する。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts\install_skill.ps1 [配置先ディレクトリ]
param(
    [string]$Destination = "$HOME\.gemini\config\skills\instant-film-agent"
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SourceFile = Join-Path $RepoRoot "skill\SKILL.md"

if (-not (Test-Path $SourceFile)) {
    Write-Error "SKILL.md が見つかりません: $SourceFile"
    exit 1
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
Copy-Item $SourceFile -Destination (Join-Path $Destination "SKILL.md") -Force
Write-Host "スキル定義を配置しました: $(Join-Path $Destination 'SKILL.md')"

$YamlFile = Join-Path $RepoRoot "skill\skill.yaml"
if (Test-Path $YamlFile) {
    Copy-Item $YamlFile -Destination (Join-Path $Destination "skill.yaml") -Force
    Write-Host "スキル定義を配置しました: $(Join-Path $Destination 'skill.yaml')"
}
