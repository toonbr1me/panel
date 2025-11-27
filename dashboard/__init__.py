import atexit
import os
import subprocess
from pathlib import Path
from shutil import which

from fastapi.staticfiles import StaticFiles

from app import app, on_startup
from app.utils.logger import get_logger
from config import DASHBOARD_PATH, DEBUG, UVICORN_PORT, VITE_BASE_API

base_dir = Path(__file__).parent
build_dir = base_dir / "build"
statics_dir = build_dir / "statics"
logger = get_logger("dashboard")


class DashboardBuildError(RuntimeError):
    """Raised when dashboard assets cannot be (re)built."""


def _bun_command(*args: str) -> list[str] | None:
    bun_path = which("bun")
    if not bun_path:
        return None
    return [bun_path, *args]


def _spawn_bun_process(cmd: list[str], **popen_kwargs) -> subprocess.Popen:
    try:
        return subprocess.Popen(cmd, **popen_kwargs)
    except FileNotFoundError as exc:
        if cmd and cmd[0].endswith("bun"):
            raise DashboardBuildError("Bun executable not found. Install Bun from https://bun.sh") from exc
        raise


def build_api_interface():
    cmd = _bun_command("run", "wait-port-gen-api")
    if not cmd:
        logger.warning(
            "Skipping dashboard API client generation because Bun is not installed. "
            "Install Bun from https://bun.sh to enable automatic builds."
        )
        return

    try:
        _spawn_bun_process(
            cmd,
            env={**os.environ, "UVICORN_PORT": str(UVICORN_PORT)},
            cwd=base_dir,
            stdout=subprocess.DEVNULL,
        )
    except DashboardBuildError:
        logger.warning(
            "Unable to start API client generation because Bun is missing. "
            "Install Bun from https://bun.sh to restore dashboard builds."
        )


def build():
    cmd = _bun_command("run", "build", "--outDir", str(build_dir), "--assetsDir", "statics")
    if not cmd:
        raise DashboardBuildError("Bun is required to build the dashboard assets.")

    proc = _spawn_bun_process(
        cmd,
        env={**os.environ, "VITE_BASE_API": VITE_BASE_API},
        cwd=base_dir,
    )
    proc.wait()
    with open(build_dir / "index.html", "r") as file:
        html = file.read()
    with open(build_dir / "404.html", "w") as file:
        file.write(html)


def run_dev():
    build_api_interface()
    cmd = _bun_command("run", "dev", "--base", os.path.join(DASHBOARD_PATH, ""))
    if not cmd:
        logger.warning("Bun is required for dashboard development server. Skipping dev server start.")
        return

    try:
        proc = _spawn_bun_process(
            cmd,
            env={**os.environ, "VITE_BASE_API": VITE_BASE_API, "DEBUG": "false"},
            cwd=base_dir,
        )
    except DashboardBuildError:
        logger.warning("Bun is required for dashboard development server. Skipping dev server start.")
        return

    atexit.register(proc.terminate)


def run_build():
    if not build_dir.is_dir():
        try:
            build()
        except DashboardBuildError as exc:
            logger.warning(
                "%s Dashboard will not be served until Bun is installed and assets are built.",
                exc,
            )
            return

    app.mount(DASHBOARD_PATH, StaticFiles(directory=build_dir, html=True), name="dashboard")
    app.mount("/statics/", StaticFiles(directory=statics_dir, html=True), name="statics")


@on_startup
def run_dashboard():
    if DEBUG:
        run_dev()
    else:
        run_build()
