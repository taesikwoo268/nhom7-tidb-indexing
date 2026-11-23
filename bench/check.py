"""Verify that this machine uses the team configuration before measuring."""

import ctypes
import hashlib
import json
import subprocess
import sys

from .config import get_machine_id, get_profile
from .environment import ROOT

PROFILE = "XS"
CONFIG_GLOBS = (
    "docker/*.compose.yml",
    "docker/*.Dockerfile",
    "docker/mysql.cnf",
    "docker/profiles/XS.yml",
    "docker/profiles/tikv-XS.toml",
    "sysbench/*.lua",
    "bench/datagen.py",
    "bench/loader.py",
    "bench/schema.py",
)


def team_hash(root=ROOT):
    """Same commit gives the same hash on every machine, whatever its line endings."""
    digest = hashlib.sha256()
    names = sorted(
        p.relative_to(root).as_posix() for g in CONFIG_GLOBS for p in root.glob(g)
    )
    for name in names:
        digest.update(name.encode())
        digest.update((root / name).read_text(encoding="utf-8").encode())
    return digest.hexdigest()[:12]


def on_ac_power():
    """True, False, or None when the operating system does not tell."""
    if sys.platform != "win32":
        return None

    class Status(ctypes.Structure):
        _fields_ = [
            ("ac", ctypes.c_ubyte),
            ("flag", ctypes.c_ubyte),
            ("percent", ctypes.c_ubyte),
            ("saver", ctypes.c_ubyte),
            ("life", ctypes.c_ulong),
            ("full", ctypes.c_ulong),
        ]

    status = Status()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        return None
    return {0: False, 1: True}.get(status.ac)


def problems(profile, docker_bytes, docker_cpus, ac, dirty):
    found = []
    if profile != PROFILE:
        found.append(f"PROFILE={profile}. Dat PROFILE={PROFILE} trong .env.")
    if docker_bytes < 9 * 1024**3:
        found.append(
            f"Docker chi co {docker_bytes / 1024**3:.1f} GiB. Dat memory=10GB, swap=4GB "
            "trong .wslconfig roi chay: wsl --shutdown"
        )
    if docker_cpus < 8:
        found.append(f"Docker chi co {docker_cpus} CPU, can it nhat 8.")
    if ac is False:
        found.append("May dang chay pin. Cam sac truoc khi do.")
    if dirty:
        found.append(f"File cau hinh khac Git: {dirty}")
    return found


def check():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()

    info = json.loads(
        subprocess.check_output(["docker", "info", "--format", "{{json .}}"], text=True)
    )
    ac = on_ac_power()
    dirty = git("status", "--porcelain", "--", "docker", "sysbench", "bench")
    print(
        f"machine={get_machine_id()} profile={get_profile()} "
        f"docker={info['NCPU']} CPU/{info['MemTotal'] / 1024**3:.1f} GiB "
        f"ac_power={ac} commit={git('rev-parse', '--short', 'HEAD')}"
    )
    print(f"team_hash={team_hash()}  (phai giong nhau tren ca ba may)")
    found = problems(get_profile(), info["MemTotal"], info["NCPU"], ac, dirty)
    if found:
        raise SystemExit("KHONG DAT:\n- " + "\n- ".join(found))
    print("DAT")
