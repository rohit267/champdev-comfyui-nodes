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
