# 回执上下文五组完整实验

19 道 fmt 缺陷任务、五组策略、每题每组两次，共 190 条轨迹。独立冷评分通过 159 条，失败 31 条；全部轨迹的用量和原件核验完整。状态组观测通过率最高、平均输入最低，状态感知压缩实际触发数为 0。局部压缩证据来自 17 次结构化诊断提取和 1 次精确结果去重。

## 成功率与完整任务用量

| 策略 | 冷评分通过 | 平均输入 Token | 输入相对基线 | 平均总 Token | 总量相对基线 |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 32/38（84.2%） | 276,489 | 基线 | 283,860 | 基线 |
| diagnostics | 33/38（86.8%） | 287,610 | +4.02% | 295,198 | +3.99% |
| dedup | 32/38（84.2%） | 276,774 | +0.10% | 283,706 | −0.05% |
| state | 35/38（92.1%） | 272,727 | −1.36% | 279,544 | −1.52% |
| combined | 27/38（71.1%） | 284,349 | +2.84% | 291,636 | +2.74% |

各组均使用全部 38 条注册轨迹计算平均值，失败样本保留在分母和用量中。总 Token 为供应方输入与输出之和，输入包含缓存命中的部分，显示值四舍五入至整数。

全批次共 **3,576 次模型请求**，其中 3,575 次修复请求、1 次通用历史摘要；累计输入 **53,122,047 Token**，累计输出 **1,367,836 Token**，输入中的缓存部分为 **43,288,960 Token**。缺失结果、未知用量、基础设施异常和自动重跑均为 0。

状态组比基线多通过 3 条、平均输入低 1.36%；其 710 次状态压缩判定全部低于触发水位。该差异按组间观测记录，状态压缩的降耗效果由实际启用并触发的对照实验评价。诊断组多通过 1 条、输入增加 4.02%，体现本批次的质量与开销取舍。

## 逐题配对

配对单位为“任务 × 重复编号”，每组对基线均有 38 对，全部结果完整。

| 对照组 | 两组均通过 | 两组均失败 | 对照组单独通过 | 基线单独通过 |
| --- | ---: | ---: | ---: | ---: |
| diagnostics | 30 | 3 | 3 | 2 |
| dedup | 29 | 3 | 3 | 3 |
| state | 30 | 1 | 5 | 2 |
| combined | 24 | 3 | 3 | 8 |

[results.json](results.json) 保存十种组间比较的逐对输入、输出和通过差值；[analysis.json](analysis.json)保存基线配对计数及十九题完整矩阵。相同题目的任务、系统提示和工具定义各有一个哈希，首请求输入各保留十个实际哈希，详细身份位于 `results.json/input_identity`。

## 实际机制触发

| 分组 / 机制 | 候选数 | 触发轨迹 | 触发次数 | 输入 → 输出字节 | 减少字节 |
| --- | ---: | ---: | ---: | ---: | ---: |
| diagnostics / 诊断提取 | 19 | 7/38 | 9 | 106,106 → 57,666 | 48,440 |
| dedup / 精确去重 | 0 | 0/38 | 0 | 0 → 0 | 0 |
| state / 状态压缩 | 0 | 0/38 | 0 | 0 → 0 | 0 |
| combined / 诊断提取 | 16 | 6/38 | 8 | 100,041 → 60,123 | 39,918 |
| combined / 精确去重 | 1 | 1/38 | 1 | 11,788 → 818 | 10,970 |
| combined / 状态压缩 | 0 | 0/38 | 0 | 0 → 0 | 0 |

17 次诊断提取覆盖 13 条轨迹，将这些触发回执的返回体积从 **206,147 字节缩减至 117,789 字节，减少 42.86%**。精确去重的一次触发减少 10,970 字节。字节统计反映对应回执的局部投影效果；整任务实际输入和输出在上表独立计量。

主要跳过原因仍与工作负载有关：诊断组 593 次、组合组 632 次工具返回属于诊断工具支持范围以外；精确去重组 581 次、组合组 600 次为首次观察。状态组与组合组分别有 710、738 次低于历史水位的判定。完整候选、尝试与跳过计数保存在 [工作流汇总](summary.md) 和原始结果中。

通用历史摘要出现一次：`trial-069 / diagnostics / fmtlib__fmt-2292 / repeat 1`。原始事件记录它发生在第 24 次请求，运行时估计由 52,252 降至 8,712，耗时 45.35 秒，后续修复请求为 0；该候选最终通过冷评分。这一现象支持继续评估更早的压缩时机。

## 失败与日志

31 条失败包括 **10 条冷构建失败、19 条冷测试失败、2 条空候选**，分布于 10 道任务。`fmt-1361` 与 `fmt-3819` 各 8 条，`fmt-2310` 为 6 条，三题合计 22/31。

已核验的具体故障包括：

- `fmt-1361`：浮点类型转换的大小断言、模板实例化/链接错误，以及浮点边界断言失败。
- `fmt-3819`：命名参数与自动/手动索引混用返回错误参数，`reserve` 场景返回内容异常。
- `fmt-2310`：零填充、显式对齐及 NaN 格式组合的输出断言失败。
- `fmt-3260`：时间格式对齐抛出 `invalid format`，以及 `chrono-test`、`compile-test` 段错误。

[逐题失败报告](failures.md)保存十九题五组矩阵、全部 31 条失败的冷评分和停止状态、日志原文片段、候选补丁及完整轨迹下载链接。`evidence/` 保存 29 个非空失败候选的冷构建/测试日志与补丁；两条空候选保留预算停止和未执行冷测试的状态。[failures.jsonl](failures.jsonl)可供程序逐条复核。

## 实验身份与核验

- 工作流：[Actions Run 42335967622](https://github.com/lilong555/ReproPatch/actions/runs/42335967622)，首次执行。
- 执行源码：`3bdd9de6bd49d4d8eba17a1f9af7b0d64a91f6ab`。
- 协议：[trigger-protocol.json](../trigger-protocol.json)，campaign 为 `context-ablation-trigger-20261106`，协议 SHA-256 为 `ca4b66d28d0467a523c8c8a5413d5132d1b0eb9deb437122ef0391f3d3b7e9b3`。
- 模型：`gpt-6-luna`，推理档位 `max`，原生 legacy 六工具。
- 每条预算：24 次模型请求、48 次工具调用、7,200 秒，全部辅助请求入账。
- 调度：最多 8 个 GitHub Actions worker；独立工作区、固定镜像和官方测试执行冷评分。
- 工作流时间：北京时间 2026-11-07 11:52:53 至 15:59:46，共 4 小时 6 分 53 秒。

190 个注册槽位、独立摘要和原始归档逐项对应；五组统计及十组配对结果复算一致。全部 190 个原始 ZIP 的 GitHub 摘要、tar 摘要、归档文件清单、模型结果、评分身份、事件顺序与 Run 身份通过核验。核验结果保存在 [verification.json](verification.json)、[evidence.jsonl](evidence.jsonl) 和 [raw-downloads.json](raw-downloads.json)。

## 复算与原始轨迹

[原始结果](results.json)、[工作流原始汇总](summary.md)、[冻结执行清单](plan.json)和[原始轨迹索引](artifacts.json)保持对应批次身份。190 条原始轨迹保留至 2026-12-07，各条链接包含真实 artifact ID 与下载摘要。

```bash
python - <<'PY'
import hashlib, json, subprocess, zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
root = Path('context-raw')
base = Path('benchmarks/context-ablation/trigger-full')
artifacts = json.loads((base / 'artifacts.json').read_text())['raw_artifacts']
receipts = {r['name']: r for r in json.loads((base / 'raw-downloads.json').read_text())['receipts']}
def fetch(artifact):
    folder = root / artifact['name']
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / 'artifact.zip'
    if not archive.exists():
        with archive.open('wb') as out:
            subprocess.run(['gh', 'api', f"repos/lilong555/ReproPatch/actions/artifacts/{artifact['id']}/zip"], stdout=out, check=True)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == artifact['digest'].removeprefix('sha256:')
    receipt = receipts[artifact['name']]
    with zipfile.ZipFile(archive) as zipped:
        for member in receipt['members']:
            assert Path(member['path']).name == member['path']
            content = zipped.read(member['path'])
            assert hashlib.sha256(content).hexdigest() == member['sha256']
            (folder / member['path']).write_bytes(content)
    (folder / 'download.json').write_text(json.dumps(receipt) + '\n')
with ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(fetch, artifacts))
PY
```

上述命令保存完整 ZIP、其三个原始成员及下载回执。核验脚本以新目录保存复算结果：

```bash
PYTHONPATH=src:scripts python scripts/report_context_results.py \
  --results benchmarks/context-ablation/trigger-full/results.json \
  --artifacts benchmarks/context-ablation/trigger-full/artifacts.json \
  --raw-dir context-raw --output context-trigger-audit --workers 4
```

后续 [提前压缩三组实验](../../context-early-20261107/README.md)使用独立冻结合同，重点检验早期文件回执的选择性提取与 16K 状态摘要，累计模型成本与最终冷评分共同评价。
