import argparse
from pathlib import Path
from .file_collection import collect_files

def main():
    parser = argparse.ArgumentParser(description="Run Snapshotter on a repo.")
    parser.add_argument("--repo", required=True, help="Path to repo (local folder)")
    parser.add_argument("--out", required=True, help="Path to write snapshot JSON")
    args = parser.parse_args()

    repo_path = Path(args.repo).resolve()
    out_path = Path(args.out).resolve()

    # TODO: implement:
    # 1) collect_files(repo_path)
    # 2) call_snapshotter_llm(files)
    # 3) validate_and_write(snapshot, out_path)

if __name__ == "__main__":
    main()
