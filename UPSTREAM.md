# UPSTREAM — 本家エンジンの出典とピン留め

- 出典: `InstantFilmFrame` (ComfyUI Custom Node)
- 同梱範囲: `src/instant_film_agent/engine/` 以下の `instant_frame.py` / `instant_config.py` と `fonts/`。ComfyUI ノード定義（`nodes.py`）や Web UI / ワークフローは含めない。
- 同梱スナップショット: 2026-11-08 時点のスナップショット。版数の固定は各ファイルの SHA-256 で行う。正本は `src/instant_film_agent/data/engine_hashes.json` で、`doctor` の `engine_integrity` が照合する。
- 同梱ファイルは原則改変しない。変更が必要になった場合は、本家へ還す改善として切り出す。
- 同期手順: `scripts/sync_upstream.py <本家チェックアウトのパス>` が差分とハッシュを表示して止まる。取り込む場合はエンジンファイルと素材を差し替え、ハッシュマニフェストを再生成し、テストを通してから確定する。自動上書きはしない。
