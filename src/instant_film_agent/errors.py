"""終了コードと機械可読エラー定義。"""
from __future__ import annotations

EXIT_OK = 0
EXIT_USAGE = 2          # 引数・設定・プリセット名エラー
EXIT_INPUT = 3          # 入力ファイル不在・未対応フォーマット
EXIT_OUTPUT_EXISTS = 4   # 出力ファイルが既に存在し --overwrite が指定されていない
EXIT_ENGINE = 5         # レンダリングエンジン内部の失敗


class AgentError(Exception):
    """CLI/JSON で構造化して返せる例外クラス。"""

    def __init__(self, code: str, exit_code: int, message: str, **extra):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code
        self.message = message
        self.extra = extra

    def to_dict(self) -> dict:
        err = {"code": self.code, "message": self.message}
        err.update(self.extra)
        return {"ok": False, "error": err}
