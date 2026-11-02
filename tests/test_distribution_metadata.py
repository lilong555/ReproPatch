"""发布版本与可选依赖在源码、项目配置和锁文件中保持一致。"""

import json
import tomllib

from conftest import ROOT

from repropatch import __version__


def test_release_version_matches_package_and_lock():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    locked = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(item for item in locked["package"] if item["name"] == "repropatch")
    release = json.loads((ROOT / "RELEASE.json").read_text())
    assert project["version"] == __version__ == package["version"] == release["product_version"]
    assert release["release_identity"]["tag"] == f"v{__version__}"


def test_lock_preserves_optional_dependency_groups():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    locked = tomllib.loads((ROOT / "uv.lock").read_text())
    package = next(item for item in locked["package"] if item["name"] == "repropatch")
    expected = set(project["optional-dependencies"])
    assert set(package["optional-dependencies"]) == expected
    assert set(package["metadata"]["provides-extras"]) == expected
