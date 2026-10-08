"""annotorch が意図して送出する例外。

呼び出し側に原因があるもの（NotFoundError / InvalidInputError / ConflictError）と、
サーバー側のデータに原因があるもの（WorkspaceError）に分かれる。
組み込み例外で捕捉する呼び出し側（datasets の利用者など）にも届くよう、
意味の近い組み込み例外も親に持たせている。
"""

from __future__ import annotations


class AnnotorchError(Exception):
    """annotorch が意図して送出する例外の基底。"""


class NotFoundError(AnnotorchError, LookupError):
    """指定されたものが存在しない。"""


class InvalidInputError(AnnotorchError, ValueError):
    """呼び出し側の入力が不正。"""


class ConflictError(AnnotorchError):
    """今の状態と衝突するため実行できない。"""


class WorkspaceError(AnnotorchError):
    """ワークスペースのデータが壊れている、または互換性がない。"""


class AnswerValidationError(InvalidInputError):
    """回答がタスクの質問タイプに合わない。"""


class ItemsInUseError(ConflictError):
    """タスクの unit から参照されているアイテムを削除しようとした。"""


class OutputExistsError(ConflictError, FileExistsError):
    """エクスポート先がすでに存在する。"""


class SchemaVersionError(WorkspaceError):
    """project.db のスキーマバージョンが対応外。"""


class ItemFileMissingError(WorkspaceError):
    """DB に登録されたアイテムのファイルがディスク上にない。"""


class NotADatasetError(InvalidInputError, FileNotFoundError):
    """指定されたディレクトリが annotorch のデータセットではない。"""
