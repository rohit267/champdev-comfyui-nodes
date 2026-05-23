import fm_core


def test_classify_kind_by_extension():
    assert fm_core.classify_kind("a.png") == "image"
    assert fm_core.classify_kind("b.JPG") == "image"
    assert fm_core.classify_kind("c.mp4") == "video"
    assert fm_core.classify_kind("d.wav") == "audio"
    assert fm_core.classify_kind("e.txt") == "text"
    assert fm_core.classify_kind("f.bin") == "other"
    assert fm_core.classify_kind("noext") == "other"
