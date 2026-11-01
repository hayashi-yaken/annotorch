import pytest

from annotorch.errors import InvalidInputError
from annotorch.server.paths import dataset_name, resolve_within


def test_resolve_within_accepts_relative_path(tmp_path):
    assert resolve_within(tmp_path, "a/b") == (tmp_path / "a" / "b").resolve()


def test_resolve_within_accepts_absolute_path_inside_root(tmp_path):
    inside = tmp_path / "a"
    assert resolve_within(tmp_path, str(inside)) == inside.resolve()


def test_resolve_within_accepts_root_itself(tmp_path):
    assert resolve_within(tmp_path, ".") == tmp_path.resolve()


@pytest.mark.parametrize("path", ["..", "../x", "a/../../x", "/etc"])
def test_resolve_within_rejects_paths_outside_root(tmp_path, path):
    with pytest.raises(InvalidInputError, match="must be inside"):
        resolve_within(tmp_path / "root", path)


def test_resolve_within_rejects_symlink_escaping_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    (root / "link").symlink_to(tmp_path)
    with pytest.raises(InvalidInputError):
        resolve_within(root, "link")


def test_dataset_name_strips_whitespace():
    assert dataset_name("  swan_vs_duck  ") == "swan_vs_duck"


def test_dataset_name_allows_non_ascii_and_spaces():
    assert dataset_name("白鳥 v2") == "白鳥 v2"
    assert dataset_name("白鳥\u3000v2") == "白鳥\u3000v2"


@pytest.mark.parametrize("name", ["", "  ", ".", "..", ".hidden", "a/b", "a\\b", "/abs",
                                  "a\nb", "a\tb", "a\x7fb"])
def test_dataset_name_rejects_paths_and_hidden_names(name):
    with pytest.raises(InvalidInputError):
        dataset_name(name)


def test_resolve_within_rejects_null_byte(tmp_path):
    with pytest.raises(InvalidInputError):
        resolve_within(tmp_path, "a\0b")


def test_dataset_name_rejects_overlong_names():
    assert dataset_name("あ" * 66) == "あ" * 66
    with pytest.raises(InvalidInputError, match="too long"):
        dataset_name("あ" * 67)
