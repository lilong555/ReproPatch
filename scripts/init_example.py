"""Create the standalone example Git repository, without touching an existing one."""

from pathlib import Path

from repropatch.workspace import git

repo = Path(__file__).resolve().parents[1] / "examples" / "cpp-bugs"
if not (repo / ".git").exists():
    git(repo, "init", "-b", "main")
    git(repo, "add", "CMakeLists.txt", "src", "tests")
    git(
        repo,
        "-c",
        "user.name=ReproPatch Example",
        "-c",
        "user.email=example@localhost",
        "commit",
        "-m",
        "Add reproducible all-negative maximum defect",
    )
print(git(repo, "rev-parse", "HEAD").strip())
