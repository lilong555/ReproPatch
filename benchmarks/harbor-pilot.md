# Harbor 产物链路

固定 Harbor 0.24.0，源码 commit 为 `6c9d3d6609854375005a7b5c8f1906371d64c6ff`。
实际安装的 401 个 Python 文件与固定源码逐字节一致；独立依赖环境见
[requirements/harbor.txt](../requirements/harbor.txt)，不与固定 Agents SDK 环境混装。

该 pilot 使用自有 negative-maximum fixture 和原生 `oracle` 确定性生产者，不调用模型。
它验证产物链路，不是 mini-SWE-agent、ReproPatch 或 Codex 的修复能力成绩。

```bash
python scripts/prepare_harbor_fixture.py \
  --producer-image repropatch-multiswe-catch2723-sanitized:0.2 \
  --output .repropatch/harbor-fixture
HARBOR_TELEMETRY=0 harbor run -c .repropatch/harbor-fixture/job.yaml
```

producer 镜像需要已经在本地准备好，包含 Git、Python 和基础 Shell；准备记录保存其实际 image ID。
Harbor 原生作业串行执行一次、重试为零，`verifier.disable=true`，显式收集
`/logs/artifacts/candidate.patch` 为 trial 下的 `artifacts/candidate.patch`。
占位 verifier 若被误调用会退出 97，不会产生虚假通过。

作业结束后，从结果中的实际 trial 名称定位补丁，再执行：

```bash
repropatch verify-patch examples/tasks/negative-maximum.v2.yaml \
  --patch TRIAL_DIR/artifacts/candidate.patch \
  --producer harbor-0.24.0-fixture \
  --producer-trace TRIAL_DIR/artifacts/manifest.json \
  --output-root .repropatch/harbor-fixture/verification --json
```

已执行记录见 [readiness.json](readiness.json) 及其完整证据附件。
原生 collection manifest 为 `ok`，Harbor 没有 verifier reward；新建 ReproPatch Run 独立验收为 `ACCEPTED`。
Harbor 用量字段保持 null；确定性生产者没有模型请求，不能将此记录混入收费模型修复率。

当前锁定版本的 Docker provider 拒绝 `network_mode=no-network`。本 pilot 使用受信任 fixture，
producer 为 root、public 网络；之后 ReproPatch 验收仍使用原有非 root、无网络容器。
这些不同权限已单列，当前链路不满足严格同模型实验的环境对齐要求。
正式实验前须解决权限及网络策略差异、接入公共官方 Oracle，再冻结全部组配置。

目前通过现有 CLI 手动连接两段执行；尚未完成通用任务导出、批次导入、消融统计和故障对照。
