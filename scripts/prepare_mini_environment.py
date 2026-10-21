"""为固定 Task 准备原生 mini-SWE-agent Docker 配置，可选执行无模型权限检查。"""

import argparse
import hashlib
import io
import json
import os
import shlex
import subprocess
import sys
import tarfile
from pathlib import Path

from repropatch.task import Task, resolve_task
from repropatch.workspace import git_tree

MINI_COMMIT = "04d809ceab9df28f9adaed044884180159172930"


def command(argv, *, cwd=None):
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    return subprocess.check_output(argv, cwd=cwd, env=env, stderr=subprocess.PIPE, timeout=30)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def scripted_check(config, source, editable, output, mini):
    # 只加载固定上游原生类，不复制 Agent 循环或模型解析器。
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(output / "mini-settings")
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    sys.path.insert(0, str(mini / "src"))
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.environments import get_environment
    from minisweagent.models.test_models import DeterministicModel, make_output

    probe = (
        "import errno,json,os,pathlib\n"
        "assert os.getuid()==65534\n"
        f"p=pathlib.Path('/src/{editable}')\n"
        "before=p.read_bytes()\n"
        "with p.open('r+b') as f: f.write(before[:1])\n"
        "assert p.read_bytes()==before\n"
        "for name in ['/src/CMakeLists.txt','/src/.permission-probe',"
        "'/etc/.permission-probe','/src/.git/config']:\n"
        " try:\n"
        "  with open(name,'ab'): pass\n"
        " except OSError as e:\n"
        "  assert e.errno in (errno.EROFS,errno.EACCES,errno.EPERM)\n"
        " else: raise AssertionError('只读边界失效: '+name)\n"
        "print(json.dumps({'uid':os.getuid(),'editable_write':True,'protected_denied':True}))"
    )
    env = None
    result = {"paid_model_requests": 0, "status": "error", "container_deleted": False}
    try:
        env = get_environment(config)
        container = env.container_id
        info = json.loads(command(["docker", "inspect", container]))[0]
        host = info["HostConfig"]
        assert host["NetworkMode"] == "none" and host["ReadonlyRootfs"]
        assert info["Config"]["User"] == "65534:65534"
        assert host["CapDrop"] == ["ALL"]
        assert host["SecurityOpt"] == ["no-new-privileges:true"]
        result["container_profile"] = {
            key: host[key]
            for key in (
                "NetworkMode",
                "ReadonlyRootfs",
                "CapDrop",
                "SecurityOpt",
                "Memory",
                "MemorySwap",
                "NanoCpus",
                "PidsLimit",
                "Tmpfs",
            )
        }
        commands = [
            "python3 -c " + shlex.quote(probe),
            "echo COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT",
        ]
        model = DeterministicModel(
            outputs=[make_output("", [{"command": text}], cost=0) for text in commands],
            cost_per_call=0,
        )
        agent = DefaultAgent(
            model,
            env,
            system_template="只执行给定的权限探针。",
            instance_template="{{task}}",
            step_limit=2,
            cost_limit=0,
            output_path=output / "scripted-trajectory.json",
        )
        final = agent.run("无模型环境检查，不修复缺陷。")
        observations = [
            item["extra"] for item in agent.messages if "returncode" in item.get("extra", {})
        ]
        assert len(observations) == 1 and observations[0]["returncode"] == 0
        assert final["exit_status"] == "Submitted"
        assert (source / editable).is_file()
        result.update(status="passed", agent_steps=agent.n_calls, observation=observations[0])
    finally:
        if env is not None and env.container_id is not None:
            container = env.container_id
            env.cleanup()
            subprocess.run(["docker", "rm", "-f", container], capture_output=True, timeout=30)
            remaining = command(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--no-trunc",
                    "--filter",
                    f"id={container}",
                    "--format",
                    "{{.ID}}",
                ]
            )
            result["container_deleted"] = not remaining.strip()
            env.container_id = None
        save(output / "scripted-check.json", result)
    if not result["container_deleted"]:
        raise RuntimeError("容器删除未确认")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--mini-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--check-scripted", action="store_true", help="仅使用上游确定性模型检查权限"
    )
    args = parser.parse_args()
    mini = args.mini_source.resolve(strict=True)
    if command(["git", "rev-parse", "HEAD"], cwd=mini).decode().strip() != MINI_COMMIT:
        parser.error("mini-SWE-agent 源码不是固定版本")
    command(["git", "diff", "--quiet", "HEAD", "--", "src"], cwd=mini)
    resolved = resolve_task(Task.load(args.task))
    task = resolved.task
    if "CMakeLists.txt" not in {item.path for item in git_tree(task.repository, task.revision)}:
        parser.error("当前权限探针需要根目录 CMakeLists.txt")
    output = args.output.resolve()
    if "," in str(output) or any("," in name for name in resolved.editable_files):
        parser.error("Docker bind 路径不能包含逗号")
    output.mkdir(parents=True, exist_ok=False)
    source = output / "source"
    raw = command(["git", "archive", task.revision], cwd=task.repository)
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        archive.extractall(source, filter="data")
    # archive 可能受 export-ignore/subst 影响；逐个核对提交 Blob 后才开放环境。
    for item in git_tree(task.repository, task.revision):
        data = (source / item.path).read_bytes()
        algorithm = "sha1" if len(item.oid) == 40 else "sha256"
        actual = hashlib.new(algorithm, f"blob {len(data)}\0".encode() + data).hexdigest()
        if actual != item.oid:
            raise RuntimeError("导出的源码与固定提交不一致")
    git = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false"]
    command([*git, "init", "--template=", "."], cwd=source)
    command([*git, "add", "-f", "."], cwd=source)
    command(
        [
            *git,
            "-c",
            "user.name=Benchmark",
            "-c",
            "user.email=benchmark@example.invalid",
            "commit",
            "-qm",
            "baseline",
        ],
        cwd=source,
    )
    resources = task.environment
    run_args = [
        "--rm",
        "--pull=never",
        "--network=none",
        "--read-only",
        "--cap-drop=ALL",
        "--security-opt=no-new-privileges:true",
        "--user=65534:65534",
        "--init",
        "--no-healthcheck",
        "--restart=no",
        "--ipc=none",
        "--log-driver=none",
        "--ulimit=nofile=256:256",
        "--ulimit=core=0:0",
        f"--pids-limit={resources.pids_limit}",
        f"--memory={resources.memory_mib}m",
        f"--memory-swap={resources.memory_mib}m",
        f"--cpus={resources.cpu_limit}",
        "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777",
        f"--tmpfs=/build:rw,exec,nosuid,nodev,size={resources.build_tmpfs_mib}m,"
        "uid=65534,gid=65534,mode=0700",
        "--mount",
        f"type=bind,source={source},target=/src,readonly",
    ]
    for name in sorted(resolved.editable_files):
        (source / name).chmod(0o666)
        run_args.extend(["--mount", f"type=bind,source={source / name},target=/src/{name}"])
    config = {
        "environment_class": "docker",
        "image": resolved.image_id,
        "cwd": "/src",
        "timeout": task.timeout_seconds,
        "container_timeout": f"{task.budget.wall_seconds}s",
        "run_args": run_args,
        "interpreter": ["bash", "-c"],
        "forward_env": [],
        "env": {
            "HOME": "/tmp",
            "TMPDIR": "/tmp",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "CMAKE_BUILD_PARALLEL_LEVEL": "2",
            "CTEST_PARALLEL_LEVEL": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": "/src",
        },
    }
    save(output / "environment.json", config)
    (output / "issue.txt").write_text(task.prompt + "\n")
    save(
        output / "preparation.json",
        {
            "schema_version": 1,
            "scope": "native_mini_environment_not_model_benchmark",
            "mini_commit": MINI_COMMIT,
            "task_sha256": resolved.task_sha256,
            "base_commit": task.revision,
            "image_id": resolved.image_id,
            "editable_files": sorted(resolved.editable_files),
            "paid_model_requests": 0,
            "strict_same_model_comparison_ready": False,
            "native_source_sha256": {
                name: hashlib.sha256((mini / "src/minisweagent" / name).read_bytes()).hexdigest()
                for name in ("agents/default.py", "environments/docker.py", "models/test_models.py")
            },
            "differences": [
                "Bash 直接原位写允许文件；ReproPatch 使用 edit_file，Shell 的 /src 只读",
                "源码目录和非允许文件只读；不可新增、删除或原子替换文件",
                "原生 Bash 可读取完整 prepared 源码；ReproPatch 文件工具按 readable 过滤",
                "mini 使用持久容器；ReproPatch Shell 使用新容器",
                "尚未配置计费模型、统一初始诊断、请求前预算预留或 Harbor 产物桥接",
            ],
        },
    )
    if args.check_scripted:
        scripted_check(config, source, sorted(resolved.editable_files)[0], output, mini)
    print(output / "environment.json")


if __name__ == "__main__":
    main()
