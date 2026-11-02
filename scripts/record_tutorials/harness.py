"""Recorder harness: throwaway DB, app server, Playwright, encode, budget."""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from my_garage.management.commands.seed_tutorial_demo import (
    DEMO_PASSWORD,
    DEMO_USERNAME,
)

from . import encode, overlays
from .flows import FLOWS

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "static" / "tutorials"
VIEWPORT = {"width": 390, "height": 844}
SELECTOR_TIMEOUT_MS = 10_000


class StepError(RuntimeError):
    pass


class Recorder:
    """What a flow sees: the page, a step log and the cursor position."""

    def __init__(self) -> None:
        self.page = None
        self.current_step = "(start)"
        self.mouse_xy = (195.0, 700.0)
        self.lines: list[str] = []

    def log(self, line: str) -> None:
        self.lines.append(line)
        print(f"  {line}", flush=True)

    def step(self, name: str) -> None:
        self.current_step = name
        self.log(f"step: {name}")
        debug_dir = os.environ.get("TUTORIALS_DEBUG_DIR")
        if debug_dir and self.page is not None:
            slug = name.replace(" ", "-")
            self.page.screenshot(
                path=str(Path(debug_dir) / f"step-{len(self.lines):02d}-{slug}.png")
            )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _env(db_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.tutorials"
    env["TUTORIALS_DB_PATH"] = str(db_path)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(REPO_ROOT / "src"), env.get("PYTHONPATH", "")]
    )
    return env


def _manage(env: dict[str, str], *args: str) -> None:
    subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )


def _start_server(env: dict[str, str], port: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("app server exited during startup")
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/accounts/login/", timeout=2
            )
            return proc
        except Exception:
            time.sleep(0.5)
    proc.terminate()
    raise RuntimeError("app server did not become ready within 60 s")


def _record(name: str, base_url: str, work: Path, violations: list[str]) -> Path:
    """Run one flow in a fresh context; return the raw WebM path."""
    from playwright.sync_api import sync_playwright  # lazy: only the recorder needs it

    flow = FLOWS[name]
    rec = Recorder()
    state_path = work / "state.json"

    def guard(route):
        host = urlparse(route.request.url).hostname
        if overlays.host_allowed(host):
            route.continue_()
        else:
            violations.append(route.request.url)
            route.abort()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            # Sign in outside the recording so the video opens on the first page.
            login_ctx = browser.new_context(viewport=VIEWPORT)
            login_ctx.set_default_timeout(SELECTOR_TIMEOUT_MS)
            login_ctx.route("**/*", guard)
            login = login_ctx.new_page()
            rec.current_step = "sign in"
            try:
                login.goto(f"{base_url}/accounts/login/")
                login.fill("#id_username", DEMO_USERNAME)
                login.fill("#id_password", DEMO_PASSWORD)
                login.click("button[type=submit]")
                login.wait_for_url(f"{base_url}/")
            except Exception as exc:
                raise StepError(f"step 'sign in' failed: {exc}") from exc
            login_ctx.storage_state(path=state_path)
            login_ctx.close()

            video_dir = work / "video"
            ctx = browser.new_context(
                viewport=VIEWPORT,
                device_scale_factor=2,
                storage_state=state_path,
                record_video_dir=str(video_dir),
                record_video_size={
                    "width": VIEWPORT["width"] * 2,
                    "height": VIEWPORT["height"] * 2,
                },
            )
            ctx.set_default_timeout(SELECTOR_TIMEOUT_MS)
            ctx.route("**/*", guard)
            overlays.install(ctx)
            rec.page = ctx.new_page()
            t0 = time.monotonic()
            try:
                rec.step("open first page")
                rec.page.goto(f"{base_url}{flow.start_path}")
                rec.page.wait_for_selector(flow.anchor, state="attached")
                rec.page.wait_for_timeout(1500)  # let the page's fade-in finish
                rec.trim_s = max(0.0, time.monotonic() - t0 - 1.5)
                flow.run(rec)
            except Exception as exc:
                debug_dir = os.environ.get("TUTORIALS_DEBUG_DIR")
                if debug_dir and rec.page is not None:
                    rec.page.screenshot(
                        path=str(Path(debug_dir) / f"{name}-failure.png")
                    )
                msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
                raise StepError(
                    f"step '{rec.current_step}' failed at {rec.page.url}: {msg}"
                ) from exc
            rec.page.wait_for_timeout(500)
            webm = Path(rec.page.video.path())
            ctx.close()  # flushes the video file
        finally:
            browser.close()
    work.joinpath("trim.txt").write_text(f"{rec.trim_s:.2f}")
    return webm


def record_one(name: str, base_url: str) -> None:
    flow = FLOWS[name]
    print(f"Recording {name}: {flow.title}", flush=True)
    work = Path(tempfile.mkdtemp(prefix=f"tut-{name}-"))
    violations: list[str] = []
    try:
        try:
            webm = _record(name, base_url, work, violations)
        except Exception as exc:
            if violations:
                raise StepError(f"blocked external request: {violations[0]}") from exc
            raise
        if violations:
            raise StepError(f"blocked external request: {violations[0]}")
        trim = float((work / "trim.txt").read_text())
        mp4, poster = work / f"{name}.mp4", work / f"{name}.jpg"
        encode.run_ffmpeg(encode.encode_args(webm, mp4, trim))
        encode.run_ffmpeg(encode.poster_args(mp4, poster, flow.poster_at_s))
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mp4, OUT_DIR / mp4.name)
        shutil.copyfile(poster, OUT_DIR / poster.name)
        print(
            f"Wrote {mp4.name} ({mp4.stat().st_size / 1024:.0f} KB) and {poster.name}"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run(names: list[str]) -> int:
    """Record ``names`` (already validated). Returns the process exit code."""
    tmp = Path(tempfile.mkdtemp(prefix="tut-db-"))
    db_path = tmp / "tutorials.sqlite3"
    server = None
    try:
        env = _env(db_path)
        _manage(env, "migrate", "--noinput")
        _manage(env, "seed_tutorial_demo")
        port = _free_port()
        server = _start_server(env, port)
        base_url = f"http://127.0.0.1:{port}"
        for name in names:
            record_one(name, base_url)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        total = encode.check_budget(OUT_DIR)
    except encode.BudgetError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"MP4 total {total / 1024 / 1024:.2f} MB (budget 6 MB)")
    return 0
