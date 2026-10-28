"""汇总跨仓库首跑的配对差异、仓库宏平均与精确 McNemar 检验。"""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from qualify_cpp_batch import save

PAIRS = [("full", "shell-only"), ("full", "no-checks")]


def exact_mcnemar(wins, losses):
    discordant = wins + losses
    if discordant == 0:
        return 1.0
    return min(
        1.0,
        2
        * sum(math.comb(discordant, index) for index in range(min(wins, losses) + 1))
        / 2**discordant,
    )


def holm(values):
    corrected, previous = [0.0] * len(values), 0.0
    for rank, index in enumerate(sorted(range(len(values)), key=lambda index: values[index])):
        previous = max(previous, min(1.0, (len(values) - rank) * values[index]))
        corrected[index] = previous
    return corrected


def analyze(value):
    rows = value["attempts"]
    tasks = defaultdict(dict)
    for row in rows:
        task, arm = row["instance_id"], row["arm"]
        if arm in tasks[task]:
            raise ValueError("CROSS_FIRST_AND_REPEAT_RESULTS_REQUIRE_SEPARATE_REPORTS")
        tasks[task][arm] = row.get("score", {}).get("accepted")
    comparisons = []
    for left, right in PAIRS:
        complete = {
            task: result
            for task, result in tasks.items()
            if type(result.get(left)) is bool and type(result.get(right)) is bool
        }
        wins = sorted(
            task for task, result in complete.items() if result[left] and not result[right]
        )
        losses = sorted(
            task for task, result in complete.items() if result[right] and not result[left]
        )
        comparisons.append(
            {
                "left": left,
                "right": right,
                "complete_pairs": len(complete),
                "pending_pairs": len(tasks) - len(complete),
                "wins": wins,
                "losses": losses,
                "paired_success_difference": (len(wins) - len(losses)) / len(complete)
                if complete
                else None,
                "p_value": exact_mcnemar(len(wins), len(losses)),
            }
        )
    for comparison, adjusted in zip(
        comparisons, holm([c["p_value"] for c in comparisons]), strict=True
    ):
        comparison["holm_adjusted_p"] = adjusted
        comparison["significant_at_0_05"] = adjusted <= 0.05 and comparison["pending_pairs"] == 0
    repositories = defaultdict(lambda: defaultdict(list))
    for task, result in tasks.items():
        repo = task.rsplit("-", 1)[0].replace("__", "/")
        for arm, accepted in result.items():
            repositories[repo][arm].append(accepted)
    repo_rows = []
    for repo, arms in sorted(repositories.items()):
        for arm, values in sorted(arms.items()):
            known = [value for value in values if type(value) is bool]
            repo_rows.append(
                {
                    "repository": repo,
                    "arm": arm,
                    "successes": sum(known),
                    "scored": len(known),
                    "registered": len(values),
                    "pending": len(values) - len(known),
                    "success_rate": sum(known) / len(known) if known else None,
                }
            )
    macro = {}
    for arm in {row["arm"] for row in rows}:
        complete = [
            row["success_rate"] for row in repo_rows if row["arm"] == arm and row["pending"] == 0
        ]
        macro[arm] = {
            "complete_repositories": len(complete),
            "success_rate": sum(complete) / len(complete) if complete else None,
        }
    return {
        "schema": "repropatch.cross-repository-analysis.v1",
        "registered_tasks": len(tasks),
        "attempts": len(rows),
        "primary_comparisons": comparisons,
        "repositories": repo_rows,
        "repository_macro_average": macro,
        "pending_scores": sum(
            type(row.get("score", {}).get("accepted")) is not bool for row in rows
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(json.loads(args.results.read_text()))
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "analysis.json", result)
    lines = [
        "# 跨仓库配对比较",
        "",
        "| 比较 | 完整配对 | 净胜题数 | McNemar p | Holm p |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in result["primary_comparisons"]:
        lines.append(
            f"| {row['left']} / {row['right']} | {row['complete_pairs']} | "
            f"{len(row['wins']) - len(row['losses'])} | {row['p_value']:.6f} | "
            f"{row['holm_adjusted_p']:.6f} |"
        )
    lines += [
        "",
        f"已登记 {result['registered_tasks']} 题、{result['attempts']} 次尝试，"
        f"待评分 {result['pending_scores']} 次。",
    ]
    (args.output / "analysis.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
