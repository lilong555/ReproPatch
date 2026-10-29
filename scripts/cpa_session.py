"""专用 SSH 隧道、CPA 重试租约与跨 Run Attempt 认领。"""

import json
import os
import socket
import subprocess
import threading
import time
from pathlib import Path


class CPASession:
    def __init__(self, evidence):
        self.evidence = Path(evidence)
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.key = Path(os.environ["CPA_SSH_KEY_FILE"])
        self.known_hosts = Path(os.environ["CPA_SSH_KNOWN_HOSTS_FILE"])
        self.identity = {
            "owner": "cross-repository-20261028",
            "member": "run-"
            + os.environ["GITHUB_RUN_ID"]
            + "-"
            + os.environ.get("CPA_JOB_MEMBER", "job"),
            "token": os.environ["CPA_LEASE_TOKEN"],
        }
        self.tunnel = None
        self.stop = threading.Event()
        self.heartbeat_error = None
        self.thread = None

    def ssh(self):
        return [
            "ssh",
            "-i",
            str(self.key),
            "-o",
            "IdentitiesOnly=yes",
            "-o",
            "BatchMode=yes",
            "-o",
            "StrictHostKeyChecking=yes",
            "-o",
            "UserKnownHostsFile=" + str(self.known_hosts),
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ServerAliveInterval=15",
            "-o",
            "ServerAliveCountMax=2",
        ]

    def rpc(self, request):
        result = subprocess.run(
            [*self.ssh(), "repropatch-actions@20.78.59.81", "lease"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode:
            raise RuntimeError("CPA_LEASE_RPC_FAILED: " + result.stdout.strip()[:200])
        value = json.loads(result.stdout)
        if "error" in value:
            raise RuntimeError(value["error"])
        with (self.evidence / "lease-events.jsonl").open("a") as stream:
            stream.write(json.dumps({"action": request["action"], "result": value}) + "\n")
        return value

    def heartbeats(self):
        while not self.stop.wait(30):
            try:
                self.rpc({**self.identity, "action": "heartbeat"})
            except Exception as error:
                self.heartbeat_error = error
                self.stop.set()

    def healthy(self):
        if self.heartbeat_error or self.tunnel is None or self.tunnel.poll() is not None:
            raise RuntimeError("CPA_TUNNEL_OR_HEARTBEAT_LOST")

    def claim(self, attempt, phase, cap=24):
        self.healthy()
        return self.rpc(
            {
                "action": "claim",
                "campaign": self.identity["owner"],
                "attempt_id": attempt,
                "run_id": os.environ["GITHUB_RUN_ID"],
                "phase": phase,
                "request_cap": cap,
            }
        )

    def __enter__(self):
        log = (self.evidence / "ssh.log").open("wb")
        self.tunnel = subprocess.Popen(
            [
                *self.ssh(),
                "-o",
                "ExitOnForwardFailure=yes",
                "-N",
                "-L",
                "127.0.0.1:18317:127.0.0.1:8317",
                "repropatch-actions@20.78.59.81",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        log.close()
        try:
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                if self.tunnel.poll() is not None:
                    raise RuntimeError("CPA_TUNNEL_START_FAILED")
                try:
                    with socket.create_connection(("127.0.0.1", 18317), timeout=1):
                        break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("CPA_TUNNEL_START_TIMEOUT")
            self.rpc({**self.identity, "action": "enter"})
            self.thread = threading.Thread(target=self.heartbeats, daemon=True)
            self.thread.start()
            return self
        except Exception:
            self.close()
            raise

    def close(self):
        self.stop.set()
        try:
            if self.thread:
                self.thread.join(timeout=35)
                try:
                    self.rpc({**self.identity, "action": "release"})
                except RuntimeError as error:
                    if "ACTIVE_MEMBERS" in str(error):
                        self.rpc({**self.identity, "action": "leave"})
                    else:
                        raise
                finally:
                    self.thread = None
        finally:
            if self.tunnel and self.tunnel.poll() is None:
                self.tunnel.terminate()
                try:
                    self.tunnel.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.tunnel.kill()
                    self.tunnel.wait()

    def __exit__(self, *_):
        self.close()
