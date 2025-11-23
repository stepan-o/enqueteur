from pathlib import Path

def collect_files(repo_path: Path):
    paths = []
    for pattern in ["loopforge/**/*.py", "scripts/**/*.py"]:
        paths.extend(repo_path.glob(pattern))

    files = []
    for p in paths:
        rel_path = p.relative_to(repo_path).as_posix()
        content = p.read_text(encoding="utf-8")
        files.append({"path": rel_path, "content": content})
    return files
