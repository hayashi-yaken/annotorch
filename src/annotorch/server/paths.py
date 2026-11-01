"""ブラウザから受け取ったパスや名前を、サーバーが決めたディレクトリの内側に限定する。"""

from __future__ import annotations

import unicodedata
from pathlib import Path

from ..errors import InvalidInputError

# ファイル名の上限 255 バイトから、作業用の ".<name>.tmp" や ".zip" の分を空けておく
MAX_NAME_BYTES = 200


def resolve_within(root: Path, path: str) -> Path:
    """root からの相対パス（または root 配下の絶対パス）を解決する。

    シンボリックリンクをたどった先が root の外なら InvalidInputError。
    """
    if "\0" in path:
        raise InvalidInputError("path must not contain a null byte")
    base = root.resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise InvalidInputError(f"path must be inside {root}: {path}")
    return target


def dataset_name(name: str) -> str:
    """エクスポートするデータセットの名前。ディレクトリ名と ZIP のファイル名に使う。"""
    name = name.strip()
    if (not name or name.startswith(".") or any(c in name for c in "/\\")
            or any(unicodedata.category(c).startswith("C") for c in name)):
        raise InvalidInputError(
            f"invalid dataset name {name!r}: use a single folder name without slashes"
            " or control characters that does not start with '.'"
        )
    if len(name.encode()) > MAX_NAME_BYTES:
        raise InvalidInputError(f"dataset name is too long (max {MAX_NAME_BYTES} bytes in UTF-8)")
    return name
