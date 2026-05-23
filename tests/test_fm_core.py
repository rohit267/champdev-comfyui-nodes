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


def test_get_properties_of_file(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello")
    props = fm_core.get_properties(str(f))
    assert props["name"] == "note.txt"
    assert props["kind"] == "text"
    assert props["size"] == 5
    assert props["is_dir"] is False


def test_get_properties_includes_image_dimensions(tmp_path):
    from PIL import Image
    img = tmp_path / "pic.png"
    Image.new("RGB", (12, 7)).save(str(img))
    props = fm_core.get_properties(str(img))
    assert props["kind"] == "image"
    assert props["width"] == 12
    assert props["height"] == 7


def test_get_properties_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        fm_core.get_properties(str(tmp_path / "nope.txt"))


def test_delete_paths_removes_files_and_folders(tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x")
    d = tmp_path / "d"
    d.mkdir()
    (d / "inner.txt").write_text("y")

    results = fm_core.delete_paths([str(f), str(d)])

    assert all(r["ok"] for r in results)
    assert not f.exists()
    assert not d.exists()


def test_delete_paths_reports_errors(tmp_path):
    results = fm_core.delete_paths([str(tmp_path / "missing")])
    assert results[0]["ok"] is False
    assert "error" in results[0]


def test_rename_path_renames_in_place(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("x")
    res = fm_core.rename_path(str(f), "new.txt")
    assert res["ok"] is True
    assert os.path.basename(res["path"]) == "new.txt"
    assert (tmp_path / "new.txt").exists()
    assert not f.exists()


def test_rename_path_rejects_separators(tmp_path):
    f = tmp_path / "old.txt"
    f.write_text("x")
    with pytest.raises(ValueError):
        fm_core.rename_path(str(f), "sub/new.txt")


def test_rename_path_rejects_existing_target(tmp_path):
    a = tmp_path / "a.txt"
    a.write_text("x")
    (tmp_path / "b.txt").write_text("y")
    with pytest.raises(FileExistsError):
        fm_core.rename_path(str(a), "b.txt")


def test_make_dir_creates_folder(tmp_path):
    res = fm_core.make_dir(str(tmp_path), "newfolder")
    assert res["ok"] is True
    assert os.path.isdir(res["path"])
    assert os.path.basename(res["path"]) == "newfolder"


def test_make_dir_rejects_separators(tmp_path):
    with pytest.raises(ValueError):
        fm_core.make_dir(str(tmp_path), "a/b")


def test_make_dir_rejects_existing(tmp_path):
    (tmp_path / "dup").mkdir()
    with pytest.raises(OSError):
        fm_core.make_dir(str(tmp_path), "dup")
