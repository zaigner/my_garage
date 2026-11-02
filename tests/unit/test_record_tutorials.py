"""Unit tests for the tutorial recorder (no browser, no ffmpeg)."""

from __future__ import annotations

import sys

import pytest
from record_tutorials import __main__ as cli
from record_tutorials import encode, overlays
from record_tutorials.flows import FLOWS


def test_registry_has_video1_only():
    assert list(FLOWS) == ["video1"]


def test_unknown_video_exits_2_and_lists_valid_names(capsys, monkeypatch):
    # The harness must not even be imported for a bad name.
    monkeypatch.setitem(sys.modules, "record_tutorials.harness", None)
    assert cli.main(["video9"]) == 2
    err = capsys.readouterr().err
    assert "video9" in err
    assert "video1" in err


def test_one_bad_name_among_good_touches_nothing(capsys, monkeypatch):
    monkeypatch.setitem(sys.modules, "record_tutorials.harness", None)
    assert cli.main(["video1", "video9"]) == 2


def test_encode_args_are_ios_safe(tmp_path):
    args = encode.encode_args(tmp_path / "in.webm", tmp_path / "out.mp4", 1.25)
    assert args[args.index("-pix_fmt") + 1] == "yuv420p"
    assert args[args.index("-movflags") + 1] == "+faststart"
    assert args[args.index("-c:v") + 1] == "libx264"
    assert "-an" in args  # no audio
    assert args[args.index("-ss") + 1] == "1.25"
    assert f"scale={encode.WIDTH}:{encode.HEIGHT}" in args[args.index("-vf") + 1]
    assert args[-1] == str(tmp_path / "out.mp4")


def test_poster_args_take_one_frame(tmp_path):
    args = encode.poster_args(tmp_path / "v.mp4", tmp_path / "v.jpg", 1.5)
    assert args[args.index("-frames:v") + 1] == "1"
    assert args[-1] == str(tmp_path / "v.jpg")


def test_budget_sums_every_mp4_and_ignores_posters(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x" * 400)
    (tmp_path / "b.mp4").write_bytes(b"x" * 500)
    (tmp_path / "a.jpg").write_bytes(b"x" * 10_000)
    assert encode.check_budget(tmp_path, limit=900) == 900


def test_budget_exceeded_raises_with_size(tmp_path):
    (tmp_path / "a.mp4").write_bytes(b"x" * 600)
    (tmp_path / "b.mp4").write_bytes(b"x" * 600)
    with pytest.raises(encode.BudgetError, match="MB"):
        encode.check_budget(tmp_path, limit=1000)


def test_default_budget_is_6_mb():
    assert encode.SIZE_BUDGET_BYTES == 6 * 1024 * 1024


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "cdn.tailwindcss.com",
        "cdn.jsdelivr.net",
        "unpkg.com",
        "cdnjs.cloudflare.com",
        "fonts.googleapis.com",
        "fonts.gstatic.com",
    ],
)
def test_allowlisted_hosts_pass(host):
    assert overlays.host_allowed(host)


@pytest.mark.parametrize(
    "host", ["example.com", "localhost", "evil.cdn.jsdelivr.net.example.org", None]
)
def test_other_hosts_are_blocked(host):
    assert not overlays.host_allowed(host)


def test_overlay_hides_embeds_while_recording():
    assert "[data-tutorial-video] { display: none !important; }" in overlays.INIT_SCRIPT


# ---------------------------------------------------------------------------
# Harness behaviour (browser, server and ffmpeg stubbed out)
# ---------------------------------------------------------------------------


@pytest.fixture
def harness(monkeypatch, tmp_path):
    from record_tutorials import harness

    out = tmp_path / "out"
    out.mkdir()
    monkeypatch.setattr(harness, "OUT_DIR", out)
    return harness


def _no_ffmpeg(args):
    raise AssertionError("ffmpeg must not run")


def test_ui_drift_writes_nothing_and_names_the_step(harness, monkeypatch):
    def drift(name, base_url, work, violations):
        raise harness.StepError("step 'tap two starters' failed at /welcome/")

    monkeypatch.setattr(harness, "_record", drift)
    monkeypatch.setattr(encode, "run_ffmpeg", _no_ffmpeg)
    with pytest.raises(harness.StepError, match="tap two starters"):
        harness.record_one("video1", "http://127.0.0.1:1")
    assert list(harness.OUT_DIR.iterdir()) == []


def test_cli_exits_non_zero_naming_the_failed_step(harness, monkeypatch, capsys):
    def fail(names):
        raise harness.StepError("step 'open the menu' failed at /welcome/")

    monkeypatch.setattr(harness, "run", fail)
    assert cli.main(["video1"]) == 1
    assert "open the menu" in capsys.readouterr().err


@pytest.mark.parametrize("flow_raises", [False, True])
def test_external_request_fails_naming_the_url(harness, monkeypatch, flow_raises):
    def call_out(name, base_url, work, violations):
        violations.append("https://generativelanguage.googleapis.com/v1/x")
        if flow_raises:
            raise RuntimeError("net::ERR_FAILED")
        return work / "raw.webm"

    monkeypatch.setattr(harness, "_record", call_out)
    monkeypatch.setattr(encode, "run_ffmpeg", _no_ffmpeg)
    with pytest.raises(harness.StepError, match="generativelanguage.googleapis.com"):
        harness.record_one("video1", "http://127.0.0.1:1")
    assert list(harness.OUT_DIR.iterdir()) == []


class _FakeServer:
    def terminate(self):
        pass

    def wait(self, timeout=None):
        return 0


def _stub_run_plumbing(harness, monkeypatch, db_paths):
    real_env = harness._env

    def env(db_path):
        db_paths.append(db_path)
        db_path.write_text("")  # stands in for the migrated DB
        return real_env(db_path)

    monkeypatch.setattr(harness, "_env", env)
    monkeypatch.setattr(harness, "_manage", lambda env, *args: None)
    monkeypatch.setattr(harness, "_start_server", lambda env, port: _FakeServer())


def test_full_run_exits_0_and_removes_the_temp_db(harness, monkeypatch):
    db_paths = []
    _stub_run_plumbing(harness, monkeypatch, db_paths)
    monkeypatch.setattr(
        harness,
        "record_one",
        lambda name, base_url: (harness.OUT_DIR / f"{name}.mp4").write_bytes(b"x"),
    )
    assert harness.run(["video1"]) == 0
    assert (harness.OUT_DIR / "video1.mp4").exists()
    assert not db_paths[0].exists() and not db_paths[0].parent.exists()


def test_over_budget_keeps_files_and_exits_non_zero(harness, monkeypatch, capsys):
    db_paths = []
    _stub_run_plumbing(harness, monkeypatch, db_paths)

    def big(name, base_url):
        with open(harness.OUT_DIR / f"{name}.mp4", "wb") as f:
            f.truncate(encode.SIZE_BUDGET_BYTES + 1)  # sparse: no real 6 MB write

    monkeypatch.setattr(harness, "record_one", big)
    assert harness.run(["video1"]) == 1
    assert (harness.OUT_DIR / "video1.mp4").exists()
    assert "6.00 MB" in capsys.readouterr().err


def test_committed_videos_are_within_budget():
    from pathlib import Path

    out_dir = Path(__file__).resolve().parents[2] / "static" / "tutorials"
    encode.check_budget(out_dir)


def test_run_uses_throwaway_db_and_tutorials_settings(monkeypatch, tmp_path):
    from record_tutorials import harness

    manage_envs, server_envs = [], []
    monkeypatch.setattr(harness, "_manage", lambda env, *a: manage_envs.append(env))

    class FakeServer:
        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass

    def fake_start(env, port):
        server_envs.append(env)
        return FakeServer()

    monkeypatch.setattr(harness, "_start_server", fake_start)
    monkeypatch.setattr(harness, "record_one", lambda name, url: None)
    monkeypatch.setattr(harness, "OUT_DIR", tmp_path)

    assert harness.run(["video1"]) == 0
    assert manage_envs and server_envs
    for env in manage_envs + server_envs:
        assert env["DJANGO_SETTINGS_MODULE"] == "config.settings.tutorials"
        assert env["TUTORIALS_DB_PATH"].endswith("tutorials.sqlite3")
    assert len({e["TUTORIALS_DB_PATH"] for e in manage_envs + server_envs}) == 1
    assert "db.sqlite3" not in {
        e["TUTORIALS_DB_PATH"].rsplit("/", 1)[-1] for e in manage_envs
    }
