<div align="center">

# 📷 instant-film-agent

### AIエージェント ＆ CLI のための本格インスタント写真フレーム ＆ 現像エミュレーションエンジン

[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg?style=flat-square)](pyproject.toml)
[![Python](https://img.shields.io/badge/python->=3.10-blue.svg?style=flat-square)](pyproject.toml)
[![Engine](https://img.shields.io/badge/engine-NumPy%20%2B%20Pillow%20(Pure)-success.svg?style=flat-square)](src/instant_film_agent/engine/)
[![Latency](https://img.shields.io/badge/latency-~200ms%20(CPU)-brightgreen.svg?style=flat-square)](tests/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square)](LICENSE)
[![Fonts](https://img.shields.io/badge/fonts-OFL%20%2F%20Free-blueviolet.svg?style=flat-square)](src/instant_film_agent/engine/fonts/LICENSE-OFL.txt)

<br />

**[🇯🇵 日本語 (Japanese)](README_JA.md)** | **[🇺🇸 English](README.md)**

<br />

[なぜこのツールなのか？](#なぜ-instant-film-agent-なのか) • [主な特長](#主な特長) • [プリセットギャラリー](#プリセットギャラリー) • [AIエージェント導入ガイド](#aiエージェント導入ガイド) • [CLI リファレンス](#cli-リファレンス) • [自然言語プロンプト例](#自然言語プロンプト例) • [FAQ](#faq)

<br />

*「単なる白枠の貼り付けではない。実在するポラロイド・チェキのミリ単位物理比率、0〜100の化学現像エミュレーション、そして余白への手書きインク質感を完全再現する。」*

</div>

---

## 💡 なぜ instant-film-agent なのか？

写真にインスタント写真風の枠を付ける際、多くのツールは **「適当な白い長方形を貼り付けて、下にテキストを置くだけ」** にとどまっています。

しかし、実際のインスタント写真（Polaroid や instax）には、独自の歴史・規格・物理構造があります：
- **ミリ単位の実寸プロポーション（リアリティ ＆ シミュラークル）**:
  - **チェキ (instax mini)**: 窓 46×62mm (≈3:4) に対し、外枠 54×86mm（クレジットカード実寸黄金比）。
  - **ポラロイド 600 / SX-70**: 正方形窓 79×79mm (1:1) に対し、外枠 88.5×107.5mm。
  - **チェキ WIDE**: 窓 99×62mm (≈16:10) に対し、外枠 108×86mm。
  - 共通する「極細の天・左右余白」と「薬液ポッドを収める分厚い下余白（アゴ）」の黄金比が、一目で誰もがポラロイドと認識できる記号性を形成しています。
- **化学現像エミュレーション（0〜100 スライダー）**:
  - `0`（完全非破壊）：元画像の色・解像度を100%維持し、フレームと文字のみを合成。
  - `1〜100`（本格化学現像）：黒浮き（Fade Black）、ハイライトロールオフ、周辺減光、ローラー薬液展開ムラ、輝度連動粒子を連続付与。
- **書き手の個性を宿す手書き文字 ＆ ペン物理質感**:
  - 油性マジックのインク溜まり・滲み、ボールペンのかすれ、銀ラメペンのキラキラ反射、白ポスカのマットな顔料感を物理シミュレート。

従来の素朴な実装と本プロジェクトの設計思想の違いは以下の通りです。

### 📊 従来手法との比較

| 項目・設計思想 | 従来の素朴な実装（四角い枠追加） | 一般的なツール / ノード | 本プロジェクト (`instant-film-agent`) |
|---|---|---|---|
| **外枠プロポーション** | 目分量の適当な余白 | 単一の正方形枠 | **実在規格（チェキmini / ポラ600 / SX-70 / WIDE）のミリ実測比率** |
| **現像エミュレート** | なし（画像そのまま） | LUT / フィルタ固定 | **0〜100 連続スライダー（0=完全非破壊、100=濃厚な化学現像）** |
| **トーン選択** | 抱き合わせ固定プリセット | 手動RGB色補正 | **構図連動 Smart Default ＆ 独立トーン（チェキ人肌、70s暖色、90s青緑、モノクロ等）** |
| **余白テキスト** | システムフォント貼り付け | 等幅英数のみ | **20種類のオープン手書きフォント ＆ インク物理再現（マジック滲み・ラメ・ポスカ等）** |
| **日付自動連携** | 手動入力のみ | 現在日付のみ | **写真の EXIF 撮影日時（DateTimeOriginal）を完全自動抽出・印字** |
| **マスク出力** | なし | 写真部分のみ | **写真窓マスク（window_mask）とカード本体マスク（card_mask）を個別出力** |
| **依存関係** | Pillow のみ | PyTorch / GPU / ComfyUI 必須 | **ピュア NumPy + Pillow（GPU不要・数十〜数百ミリ秒動作）** |
| **AIエージェント親和性** | なし（手動UI専用） | ノード接続UIのみ | **JSON入出力・能力カタログ・自己診断（`doctor`）・自然言語スキル完備** |

---

## 🌟 主な特長

- 📐 **実在する 3 大インスタントフィルム規格のミリ実測プロポーション**  
  現代の AI 生成画像（縦長ポートレート）に最適なチェキ縦長（`Portrait (Vertical)`）、ポラロイド正方形（`Square (Polaroid)`）、風景・集合写真向けワイド（`Landscape (Wide)`）を網羅。
- 🔄 **構図の自動判別（`Auto Aspect`）＆ 非トリミング（`Keep Aspect`）**  
  元画像の縦横比から最適なフィルム規格を自動判定する `Auto Aspect` や、画像を一切切り抜かずに黄金比カードを付与する `Keep Aspect` を搭載。
- 🧪 **0〜100 連続化学現像エミュレーション**  
  スライダー `0` では元画像ピクセルを 1 ピクセルも変えずにフレームのみ合成。数値を上げるとローラー薬液ムラ、黒浮き、トイレンズ微色収差、銀塩粒子が有機的に付与されます。
- 📷 **写真の EXIF 撮影日時を完全自動抽出（`--date photo`）**  
  昔の写真やスマホで撮った写真から当時の撮影日時を自動抽出し、手書きスタンプとして余白に焼き付けます。
- ✒️ **20 種類の高品質オープン手書きフォント ＆ インク物理シミュレーション**  
  日常日記ペン、かわいい丸文字、極細ボールペン、アンティーク万年筆、筆文字、太字マーカー等を同梱。フォント別の視覚サイズ自動正規化、ベースラインのゆらぎ、油性マジックや銀ペンの質感を再現。
- 🎭 **写真窓 ＆ 外枠カードのマスク同時出力（`--save-masks`）**  
  後続のエージェント処理や Photoshop 等での加工に便利な透明度マスクを PNG で出力可能。
- ⚡ **超軽量 ＆ 高速（PyTorch / GPU / ComfyUI 不要）**  
  純粋な NumPy + Pillow のみで実装されており、ComfyUI や GPU は不要。CPU のみで軽快に動作します。

---

## 🎨 プリセットギャラリー

ワンタッチで呼び出せる代表的なスタイルプリセットを完備：

| プリセット名 (`--preset`) | エイリアス | 構図規格 | 現像トーン | 推奨用途・特徴 |
|---|---|---|---|---|
| **`instax-mini`** *(既定)* | `cheki`, `チェキ` | 縦長チェキ (46×62mm) | Modern Clear (ハイキー) | 現代チェキ風人肌透明感、日常日記ペン |
| **`polaroid-600`** | `polaroid`, `ポラロイド` | 正方形 (79×79mm) | Cool Cyan (90s青緑) | 90年代ポラロイド特有の爽やかな青緑黒浮き、太字メモ |
| **`polaroid-sx70`** | `sx70`, `70s` | 正方形 (79×79mm) | Warm Amber (70s暖色) | 70年代SX-70琥珀色ハイライト、温白色用紙、万年筆 |
| **`instax-wide`** | `wide`, `ワイド` | 横長ワイド (99×62mm) | Cool Cyan (90sスナップ) | パノラマ・集合写真・旅の風景、ゲル青インク |
| **`pastel-dream`** | `pastel`, `kawaii` | 縦長チェキ | Pastel Muted (淡色軟調) | ふんわり白浮き、アイドルチェキ、丸文字、銀ラメペン |
| **`vivid-summer`** | `summer`, `vivid` | 正方形ポラロイド | Vivid Pop (夏・高彩度) | 原色が弾けるストリート感、赤サインペン |
| **`classic-monochrome`**| `bw`, `モノクロ` | 正方形ポラロイド | Classic B&W (純銀塩白黒) | 温黒調階調、筆文字スタイル、銀塩ノイズ |
| **`cinematic-night`** | `cinematic` | 横長ワイド | Cinematic Teal (映画調) | 黒台紙フレーム、ティール黒浮き、夜景、白ポスカ |
| **`aged-nostalgia`** | `vintage` | 正方形ポラロイド | Warm Amber (劣化暖色) | 経年劣化エイジング用紙、アンティーク万年筆 |
| **`auto-smart`** | `auto` | 画像比率自動判別 | 連動 Smart Default | 入力画像の向きに合わせて構図・トーンを全自動決定 |
| **`keep-aspect-clean`** | - | 縦長チェキ | 連動 Smart Default | 元画像比率を100%維持（トリミングなし） |

---

## 🗣️ 自然言語プロンプト例

AI エージェント（Antigravity / Gemini / Claude 等）に自然な日本語で話しかけるだけで、適切なプリセットとパラメータを自動適用します：

* *「この写真をチェキ風にして、余白に手書きで "Tokyo Stroll" って入れて」*  
  → `instax-mini` プリセットを適用し、キャプション `"Tokyo Stroll"` を日記ペンで記入。
* *「ポラロイド風に枠をつけて。撮影日時も入れて」*  
  → `polaroid-600` を適用し、EXIF から撮影日時を抽出して印字。
* *「昔のSX-70みたいにレトロな暖色ポラにして」*  
  → `polaroid-sx70`（暖色トーン・温白用紙・万年筆）を適用。
* *「色はそのままでいいから、チェキの枠だけつけて」*  
  → `--emulation 0`（完全非破壊）でフレームのみ合成。
* *「画像の比率を崩さず、黒枠のインスタント写真にして」*  
  → `--fit "Keep Aspect" --paper "Matte Black"` を適用。

---

## 🛠️ CLI リファレンス

### 基本コマンド
```bash
# 最もシンプルな実行（既定のチェキ風お気に入りを適用）
instant-film-agent apply input.jpg --json

# プリセット指定 + キャプション記入 + EXIF撮影日印字
instant-film-agent apply photo.jpg -p polaroid-600 -c "Summer Memories" -d photo --json

# 写真窓・カード外枠のマスクも同時保存
instant-film-agent apply input.jpg -o out.jpg --save-masks --json

# 完全非破壊（色調変更なし・枠と文字のみ合成）
instant-film-agent apply input.jpg --emulation 0 --json

# ディレクトリ一括処理
instant-film-agent batch ./photos -o ./instant_photos -p instax-mini --json
```

### 管理・診断コマンド
```bash
# 環境・エンジン整合性・フォント完全性チェック
instant-film-agent doctor --json

# 利用可能な全機能・全パラメータのカタログ取得
instant-film-agent capabilities --json

# プリセット一覧表示
instant-film-agent presets list --json

# プリセット詳細表示
instant-film-agent presets show polaroid-sx70 --json

# デフォルトのお気に入りプリセット変更
instant-film-agent favorite polaroid-600 --json
```

### 主要オプション一覧
| オプション | 短縮 | 説明 | 指定例 |
|---|---|---|---|
| `--preset` | `-p` | スタイルプリセット名またはエイリアス | `instax-mini`, `polaroid-600`, `cheki`, `sx70` |
| `--format` | - | 構図規格 | `Portrait (Vertical)`, `Square (Polaroid)`, `Landscape (Wide)` |
| `--fit` | - | アスペクト適合方式 | `Crop to Window`, `Auto Aspect`, `Keep Aspect` |
| `--crop-pos` | - | クロップ位置 | `Center`, `Top`, `Bottom`, `Left`, `Right` |
| `--tone` | - | フィルム現像トーン | `Modern Clear (instax)`, `Warm Amber (70s Vintage)` 等 |
| `--emulation` | - | 現像強度（0〜100、0=非破壊） | `0`, `65`, `85` |
| `--paper` | - | 印画紙カラー | `Pure White`, `Warm Ivory`, `Aged Vintage`, `Matte Black` |
| `--paper-texture` | - | 印画紙テクスチャ粗さ (0〜100) | `30` (既定) |
| `--caption` | `-c` | 余白手書きキャプション文字列 | `"Memories with Friends"` |
| `--date` | `-d` | 日付モード | `photo` (EXIF撮影日), `today`, `random`, `none`, または任意文字列 |
| `--at` | - | 撮影日時直接指定 | `1999-07-24` または `1999-07-24T15:30` |
| `--style` | - | 手書きフォントスタイル | `Diary Pen (Casual Notes)`, `Cute Round Pop (Kawaii)` 等 |
| `--ink` | - | インクカラー＆物理プロファイル | `Marker Black (Permanent)`, `Silver Gel (Glitter)` 等 |
| `--save-masks`| - | 写真窓と外枠カードの PNG マスクを保存 | フラグ指定 |
| `--overwrite` | - | 出力ファイル重複時に強制上書き | フラグ指定 |
| `--json` | - | 機械可読な JSON 形式で出力 | フラグ指定 |

---

## 🤖 AIエージェント導入ガイド

本ツールは AI エージェントの自律ツールとして最適化されています。

### 導入手順
```bash
# 1. パッケージのインストール
pip install -e .

# 2. 正常動作の確認
instant-film-agent doctor --json
# => {"ok": true, ...} が返れば準備完了

# 3. エージェント用スキルの配置 — 配置先はキーワードで選べる
#    muse:   ~/workspace/custom-skills/instant-film-agent (Muse 用)
#    gemini: ~/.gemini/config/skills/instant-film-agent (Gemini CLI / Antigravity 用、既定)
#    任意のパスを直接渡すこともでき、環境変数 INSTANT_FILM_SKILL_DEST でも指定できる
powershell -ExecutionPolicy Bypass -File scripts/install_skill.ps1 muse
# (Linux / Mac の場合: bash scripts/install_skill.sh muse)
```

---

## 📄 ライセンス

- コード: [MIT License](LICENSE)
- 同梱フォント: [SIL Open Font License 1.1 / フリーライセンス](src/instant_film_agent/engine/fonts/LICENSE-OFL.txt)（商用利用可能・自己完結同梱）
- アップストリーム元: [`InstantFilmFrame`](https://github.com/treeturtlefall-arch/InstantFilmFrame)
