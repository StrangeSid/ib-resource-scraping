"""Clone the 8 self-host repos (git host has no challenge)."""
import subprocess
from pathlib import Path
from .. import config


def mirror(dest, depth=1):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    done = {}
    for repo in config.GIT_REPOS:
        target = dest / repo
        if target.exists():
            done[repo] = "exists"
            continue
        p = subprocess.run(["git", "clone", "--depth", str(depth),
                            f"{config.GIT_ORG}/{repo}.git", str(target)],
                           capture_output=True, text=True, timeout=1800)
        done[repo] = "cloned" if p.returncode == 0 else f"fail: {p.stderr[-200:]}"
    return done
