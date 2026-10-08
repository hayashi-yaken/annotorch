from __future__ import annotations

import copy
from typing import Any

from uvicorn.config import LOGGING_CONFIG


def build_log_config(level: str) -> dict[str, Any]:
    """uvicorn のログ設定に annotorch のロガーを足したもの。

    uvicorn と同じ標準エラーに同じ見た目で出し、行にロガー名を入れて区別できるようにする。
    """
    config = copy.deepcopy(LOGGING_CONFIG)
    config["formatters"]["annotorch"] = {
        **config["formatters"]["default"],
        "fmt": "%(levelprefix)s %(name)s: %(message)s",
    }
    config["handlers"]["annotorch"] = {
        **config["handlers"]["default"],
        "formatter": "annotorch",
    }
    config["loggers"]["annotorch"] = {
        "handlers": ["annotorch"],
        "level": level.upper(),
        "propagate": False,
    }
    return config
