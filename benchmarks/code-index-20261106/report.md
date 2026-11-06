# 结构化检索与缓存确定性实验

固定三份真实 fmt 头文件、12 个独立标注目标定义后，结构化查询返回体积更大，目标覆盖少一项；同源码缓存避免重复解析，单文件内容变更触发单文件重解析。全部实验为本机确定性执行，模型调用为零。

## 查询结果

| 指标，12 次查询合计 | production search_code | SemanticState.query definitions |
| --- | ---: | ---: |
| UTF-8 JSON 返回体积 / 字节 | 6,419 | 42,518 |
| 返回结果数 | 59 | 59 |
| 独立目标定义覆盖 | 12/12 | 11/12 |
| 结果集截断查询数 | 0 | 0 |
| 文本预览达到长度上限的记录数 | 0 | 14 |

两组使用相同符号字符串与三文件授权范围。文本搜索匹配大小写敏感的字面行，包含注释及使用位置；结构化查询匹配定义/声明记录的名称或文本，可能返回包含目标调用的其他函数。结果数分别计行与语法记录，跨查询重复保留。

Gold 在执行查询前由人工阅读源码确定，每文件四个目标，以唯一源码锚点冻结行号、符号和类型。文本搜索覆盖要求返回目标锚点行；结构化覆盖要求路径、符号、类型及位置吻合。评分对象为指定目标，完整定义召回与结果精确率留空。

`basic_cstring_view` 类目标未被结构化结果覆盖：相关区域出现 `variable_declaration` 记录，另有构造函数及别名记录。三个含宏的原始头文件均报告 `parse_has_error=true`，索引记录上限均未触发。结构化结果中的 14 条文本预览达到 600 UTF-8 字节上限，结果集截断与文本预览上限分别记录。详见 [逐查询 CSV](queries.csv)、[完整 JSON](queries.json) 和 [缺失目标原始返回](raw/basic_cstring_view-definitions.json)。

体积采用公开实现相同的规范 JSON 序列化，计量 runtime 包装与输出折叠之前的完整返回对象，包括结构化元数据。这里报告返回体积，工具步数、Token、任务与模型收益均未测量。

## 缓存与失效

| 条件，各 5 次 | 墙钟中位数 / ms | 最小至最大 / ms | 每次解析 / 缓存命中 |
| --- | ---: | ---: | ---: |
| 初次索引 | 14.132 | 14.026–17.741 | 3 / 0 |
| 同源码缓存 | 0.517 | 0.503–0.597 | 0 / 3 |

每组创建全新 `SemanticState`，随后立即重复相同 `definitions("write_buffer")` 查询。两条件返回内容逐组完全一致；五组全部保留，包括首次加载解析器的样本。初次索引表示应用索引为空，操作系统文件缓存与同机负载保持自然状态。计时包含授权读取、SHA-256、索引查询，采用本地输入副本适配器；生产 Worktree 编排位于测量范围之外。同源码缓存仍读取文件并计算哈希。见 [全部计时](timings.csv)。

失效检查在副本中将 `file_access_tag` 重命名为 `benchmark_file_access_tag`，保持既有缓存并重新查询：文件哈希变化、解析增量 1、其他文件缓存命中增量 2，新定义可见、旧类定义记录为 0。原始输入随后恢复并逐文件核验哈希。见 [完整记录](invalidation.json)。

## 来源与复算

ReproPatch 固定公开提交：`9cf01099206131ba6f984661a97f7aa65ee8b68a`，Apache-2.0。执行直接导入已逐文件对照 Git 对象的干净公开源码，通过独立包名隔离工作区版本。

fmt 固定提交：`0fc31633e7d53ac895ae0a688b83b7d44f0b0c1f`，MIT。输入为 `include/fmt/{args,ostream,os}.h`，共 25,053 字节，另保留完整 LICENSE。选择规则为三份较小可选头文件、每文件四个明确目标，属于小型定向样本。

输入及许可归档：[fmt-input.tar](fmt-input.tar)、[public-source.tar](public-source.tar)。[冻结协议](protocol.json) 保存全部文件与归档 SHA-256、Gold、限制和执行脚本 SHA；[driver.py](driver.py) 为该 SHA 对应的执行脚本。[环境](environment.json)：WSL2 x86_64、Python 3.12.15、tree-sitter 0.25.2、tree-sitter-cpp 0.23.4。

在 engineering 目录执行归档复算，输出使用新目录：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/benchmark_code_index.py \
  --replay benchmarks/code-index-20261106 \
  --output benchmarks/code-index-20261106/replay-new
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_code_index_benchmark.py
.venv/bin/ruff check --no-cache scripts/benchmark_code_index.py tests/test_code_index_benchmark.py
```

已完成一次独立归档复算，24 份查询返回与首轮完全一致；复算的五组计时单独保留于 [replay-verification](replay-verification/summary.json)，正文计时仍采用首轮预登记样本。Focused tests 为 5 passed，Ruff 通过；输出见 [focused-tests.txt](focused-tests.txt)、[ruff.txt](ruff.txt)。
