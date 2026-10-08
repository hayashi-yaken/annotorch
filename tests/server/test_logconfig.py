import io
import logging
import logging.config

from annotorch.server.logconfig import build_log_config


def test_annotorch_logger_has_its_own_stderr_handler():
    config = build_log_config("warning")
    logger = config["loggers"]["annotorch"]
    assert logger["level"] == "WARNING"
    assert logger["propagate"] is False
    [name] = logger["handlers"]
    assert config["handlers"][name]["stream"] == "ext://sys.stderr"
    assert "uvicorn" in config["loggers"]


def test_lines_carry_the_logger_name(monkeypatch):
    stream = io.StringIO()
    monkeypatch.setattr("sys.stderr", stream)
    logging.config.dictConfig(build_log_config("debug"))
    logging.getLogger("annotorch.server").warning("GET /api/x -> 404 NotFoundError: no x")
    assert stream.getvalue().strip() == (
        "WARNING:  annotorch.server: GET /api/x -> 404 NotFoundError: no x")
