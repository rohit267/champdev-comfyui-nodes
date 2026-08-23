import telemetry


EXPECTED_KEYS = {
    "install_id", "event_ts", "comfy_port", "comfy_listen", "private_ip",
    "public_ip", "os", "os_release", "os_version", "arch", "hostname",
    "python_version", "comfy_version", "pack_version", "cpu_model", "cpu_count",
    "ram_gb", "gpu_name", "vram_gb", "token",
}


def test_gather_payload_has_expected_keys(monkeypatch):
    # Stub the network-touching helpers so the test stays hermetic.
    monkeypatch.setattr(telemetry, "_public_ip", lambda: "203.0.113.9")
    monkeypatch.setattr(telemetry, "_private_ip", lambda: "192.168.1.5")
    monkeypatch.setattr(telemetry, "_auth_token", lambda: "tok-abc")
    payload = telemetry.gather_payload()
    assert set(payload.keys()) == EXPECTED_KEYS
    assert payload["os"]  # platform.system() is always present
    assert payload["event_ts"]
    assert payload["private_ip"] == "192.168.1.5"
    assert payload["public_ip"] == "203.0.113.9"
    assert payload["token"] == "tok-abc"


def test_gather_payload_never_raises_without_optional_deps(monkeypatch):
    # Simulate torch / psutil / nvidia-smi / comfy all being unavailable.
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name in ("torch", "psutil", "comfy", "comfy.cli_args",
                    "comfyui_version", "server"):
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    def boom(*a, **k):
        raise OSError("no nvidia-smi")

    monkeypatch.setattr(telemetry.subprocess, "run", boom)

    import urllib.request

    def no_net(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", no_net)

    payload = telemetry.gather_payload()
    assert payload["gpu_name"] is None
    assert payload["vram_gb"] is None
    assert payload["public_ip"] is None  # network unreachable → swallowed
    assert payload["token"] is None  # password_auth import stubbed out
    assert set(payload.keys()) == EXPECTED_KEYS


def test_kill_switch_suppresses_send(monkeypatch):
    telemetry._sent = False
    called = []
    monkeypatch.setattr(telemetry, "_run", lambda: called.append(True))
    monkeypatch.setenv("CHAMPDEV_TELEMETRY", "0")

    telemetry.maybe_send()

    assert called == []


def test_sends_only_once_per_process(monkeypatch):
    telemetry._sent = False
    starts = []

    class FakeThread:
        def __init__(self, *a, **k):
            self._target = k.get("target")

        def start(self):
            starts.append(True)

    monkeypatch.setattr(telemetry.threading, "Thread", FakeThread)
    monkeypatch.delenv("CHAMPDEV_TELEMETRY", raising=False)

    telemetry.maybe_send()
    telemetry.maybe_send()
    telemetry.maybe_send()

    assert len(starts) == 1


def test_post_sets_non_default_user_agent(monkeypatch):
    # Cloudflare in front of the server 403s the default "Python-urllib" UA,
    # so _post must send a custom User-Agent.
    import urllib.request

    captured = {}

    class _FakeResp:
        def close(self):
            pass

    def fake_urlopen(req, timeout=None):
        captured["req"] = req
        return _FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    telemetry._post("https://example.com", {"install_id": "x"})

    req = captured["req"]
    ua = req.get_header("User-agent")
    assert ua and not ua.lower().startswith("python-urllib")
    assert "champdev" in ua.lower()
    assert req.full_url.endswith("/ingest")


def test_public_ip_returns_none_on_failure(monkeypatch):
    import urllib.request

    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert telemetry._public_ip() is None


def test_private_ip_is_a_string_or_none():
    result = telemetry._private_ip()
    assert result is None or isinstance(result, str)


def test_server_url_env_override(monkeypatch):
    monkeypatch.setenv("CHAMPDEV_TELEMETRY_URL", "https://my.host")
    assert telemetry._server_url() == "https://my.host"
    monkeypatch.delenv("CHAMPDEV_TELEMETRY_URL", raising=False)
    assert telemetry._server_url() == telemetry.DEFAULT_TELEMETRY_URL
