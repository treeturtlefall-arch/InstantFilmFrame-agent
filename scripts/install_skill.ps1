# AIエージェントの skills へ SKILL.md / skill.yaml を配置する。
# 使い方: powershell -ExecutionPolicy Bypass -File scripts\install_skill.ps1 [muse|gemini|<配置先パス>]
#   muse        -> $HOME\workspace\custom-skills\instant-film-agent (Muse)
#   gemini      -> $HOME\.gemini\config\skills\instant-film-agent (Gemini CLI / Antigravity、既定)
#   antigravity -> gemini と同じ
#   <パス>      -> そのディレクトリへそのまま配置する (従来互換)
# 環境変数 INSTANT_FILM_SKILL_DEST でも指定できる (引数が優先、無指定時の既定は gemini)。
param(
    [string]$Destination = ""
)

if (-not $Destination) { $Destination = $env:INSTANT_FILM_SKILL_DEST }
if (-not $Destination) { $Destination = "gemini" }

switch ($Destination) {
    "muse" { $Dest = Join-Path $HOME "workspace\custom-skills\instant-film-agent" }
    "gemini" { $Dest = Join-Path $HOME ".gemini\config\skills\instant-film-agent" }
    "antigravity" { $Dest = Join-Path $HOME ".gemini\config\skills\instant-film-agent" }
    default { $Dest = $Destination }
}

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$SourceFile = Join-Path $RepoRoot "skill\SKILL.md"

if (-not (Test-Path $SourceFile)) {
    Write-Error "SKILL.md が見つかりません: $SourceFile"
    exit 1
}

New-Item -ItemType Directory -Path $Dest -Force | Out-Null
Copy-Item $SourceFile -Destination (Join-Path $Dest "SKILL.md") -Force
Write-Host "スキル定義を配置しました: $(Join-Path $Dest 'SKILL.md')"

$YamlFile = Join-Path $RepoRoot "skill\skill.yaml"
if (Test-Path $YamlFile) {
    Copy-Item $YamlFile -Destination (Join-Path $Dest "skill.yaml") -Force
    Write-Host "スキル定義を配置しました: $(Join-Path $Dest 'skill.yaml')"
}
