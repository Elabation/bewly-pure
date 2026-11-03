"""Build/publish the lightweight discovery page at the established URL."""
from pathlib import Path
import subprocess
from discovery_site import build_site

PUBLIC_PATHS = ["god-shelf.html", "index.html", "docs/god-shelf.html", "discovery-data",
                "discovery-assets.json", "discovery-status.json", "assets/bocchi-livehouse-v1.webp", "assets/livehouse-room-v6.webp", "assets/fonts", "assets/music/playlist.json", "assets/covers"]


def git(root, *args):
    result = subprocess.run(["git"] + list(args), cwd=str(root), capture_output=True,
                            text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError("git " + args[0] + " failed: " + (result.stderr or result.stdout)[-1200:])
    return result.stdout.strip()


def rebuild(root, rows=None, meta=None):
    root = Path(root)
    if rows is None:
        from review_miner import catalog
        rows, meta = catalog(root)
    from discovery_site import prepare_streams
    from discovery_covers import ensure_covers
    ensure_covers(prepare_streams(rows)[0], root)
    result = build_site(rows, meta, root, root)
    redirect = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="refresh" content="0;url={url}"><title>每日视频目录</title><a href="{url}">打开每日视频目录 →</a></html>'
    (root / "index.html").write_text(redirect.format(url="god-shelf.html"), encoding="utf-8")
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs/god-shelf.html").write_text(redirect.format(url="../god-shelf.html"), encoding="utf-8")
    return result


def publish(root, message):
    if git(root, "diff", "--cached", "--name-only"):
        raise RuntimeError("已有暂存改动，自动发布停止，避免提交无关内容。")
    git(root, "add", "-A", "--", *PUBLIC_PATHS)
    if git(root, "diff", "--cached", "--name-only"):
        git(root, "commit", "-m", message)
    git(root, "push", "origin", "main")
    return git(root, "rev-parse", "HEAD")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    print(rebuild(root))
    if args.publish:
        print(publish(root, "每日视频目录更新"))
