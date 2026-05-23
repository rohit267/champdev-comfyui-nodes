import fm_core
import os
import pytest


def test_classify_kind_by_extension():
    assert fm_core.classify_kind("a.png") == "image"
    assert fm_core.classify_kind("b.JPG") == "image"
    assert fm_core.classify_kind("c.mp4") == "video"
    assert fm_core.classify_kind("d.wav") == "audio"
    assert fm_core.classify_kind("e.txt") == "text"
    assert fm_core.classify_kind("f.bin") == "other"
    assert fm_core.classify_kind("noext") == "other"


def test_safe_realpath_normalizes_and_expands(tmp_path):
    sub = tmp_path / "a" / ".." / "b"
    (tmp_path / "b").mkdir()
    resolved = fm_core.safe_realpath(str(sub))
    assert resolved == os.path.realpath(str(tmp_path / "b"))


def test_safe_realpath_rejects_empty():
    with pytest.raises(ValueError):
        fm_core.safe_realpath("")


def test_list_dir_returns_sorted_entries(tmp_path):
    (tmp_path / "z_folder").mkdir()
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.txt").write_text("hello")
    (tmp_path / ".hidden").write_text("secret")

    result = fm_core.list_dir(str(tmp_path))

    assert result["cwd"] == os.path.realpath(str(tmp_path))
    assert result["parent"] == os.path.realpath(str(tmp_path.parent))
    names = [e["name"] for e in result["entries"]]
    # folders first, then files; hidden excluded by default
    assert names == ["z_folder", "a.png", "b.txt"]

    folder = result["entries"][0]
    assert folder["is_dir"] is True
    assert folder["kind"] == "folder"

    png = result["entries"][1]
    assert png["is_dir"] is False
    assert png["kind"] == "image"
    assert png["size"] == 1
    assert png["ext"] == ".png"
    assert "mtime" in png and "ctime" in png


def test_list_dir_can_include_hidden(tmp_path):
    (tmp_path / ".hidden").write_text("secret")
    names = [e["name"] for e in fm_core.list_dir(str(tmp_path), show_hidden=True)["entries"]]
    assert ".hidden" in names


def test_list_dir_errors_on_missing_and_nondir(tmp_path):
    with pytest.raises(FileNotFoundError):
        fm_core.list_dir(str(tmp_path / "nope"))
    f = tmp_path / "f.txt"
    f.write_text("x")
    with pytest.raises(NotADirectoryError):
        fm_core.list_dir(str(f))
