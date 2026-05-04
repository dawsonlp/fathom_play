"""Compare Claude Sonnet and Opus against the gemma4:e2b V4 pipeline baseline.

Uses only local experiment artifacts. No Fathom API calls.

This experiment runs the same V4 context-aware action-item classifier prompt
(prompt_v4_context_classifier.md) through claude-sonnet-4-6 and claude-opus-4-7,
using the same candidate and context pack inputs as the gemma4 repaired baseline.

Key questions:
- Do cloud models follow coverage rules without per-slice repair?
- Do they improve precision (fewer hard-negative promotions)?
- What is the cost/benefit difference between Sonnet and Opus?

Default models: claude-sonnet-4-6, claude-opus-4-7
Baseline: action_items-v4-repaired-140341999-20260503-165550
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv(os.path.expanduser("~/.env"))

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
PROMPT_PATH = ROOT / "targets" / "action_items" / "prompt_v4_context_classifier.md"

SYSTEM_PROMPT = (
    "You classify action-item candidates using a compact context pack. "
    "Return only valid JSON matching the requested schema exactly. "
    "Obey the hard negative rules. "
    "Your response must begin with { and end with }. "
    "Never use ```json, ```, or any other code fence or wrapper."
)

HARD_NEGATIVE_IDS = {
    "slice_01_00:00_05:00_candidate_01",
    "slice_01_00:00_05:00_candidate_02",
    "slice_03_10:00_15:00_candidate_01",
    "slice_08_35:00_40:00_candidate_01",
    "slice_08_35:00_40:00_candidate_02",
    "slice_09_40:00_45:00_candidate_01",
    "slice_09_40:00_45:00_candidate_02",
}

DEFAULT_MODELS = ["claude-sonnet-4-6", "claude-opus-4-7"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Claude models against gemma4 V4 pipeline baseline.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--candidate-run", required=True, help="V2 candidate source run ID")
    parser.add_argument("--context-run", required=True, help="Context preprocessing run ID")
    parser.add_argument(
        "--baseline-run",
        default="",
        help="Gemma4 repaired baseline run ID for comparison (optional)",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="Claude model names to compare (default: claude-sonnet-4-6 claude-opus-4-7)",
    )
    args = parser.parse_args()

    recording_dir = RUNS_DIR / str(args.recording_id)
    candidate_dir = recording_dir / args.candidate_run
    context_dir = recording_dir / args.context_run

    if not candidate_dir.exists():
        raise SystemExit(f"Candidate run not found: {candidate_dir}")
    if not context_dir.exists():
        raise SystemExit(f"Context run not found: {context_dir}")

    candidate_summary = read_json(candidate_dir / "summary.json")
    context_pack = read_json(context_dir / "deterministic_context_pack.json")
    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")

    baseline_summary: dict[str, Any] | None = None
    if args.baseline_run:
        baseline_path = recording_dir / args.baseline_run / "summary.json"
        if baseline_path.exists():
            baseline_summary = read_json(baseline_path)
        else:
            print(f"[warn] Baseline run not found at {baseline_path}, skipping comparison.")

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"claude-model-comparison-{args.recording_id}-{timestamp}"
    run_dir = recording_dir / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    write_json(
        run_dir / "manifest.json",
        {
            "experiment_id": experiment_id,
            "recording_id": args.recording_id,
            "target": "action_items",
            "vertical_variant": "v4_context_classifier",
            "candidate_run": args.candidate_run,
            "context_run": args.context_run,
            "baseline_run": args.baseline_run or None,
            "prompt_path": str(PROMPT_PATH.relative_to(ROOT)),
            "models": args.models,
            "created_at": datetime.now(UTC).isoformat(),
            "uses_fathom_api": False,
        },
    )

    arm_summaries: list[dict[str, Any]] = []
    for model_name in args.models:
        print(f"\n{'='*60}")
        print(f"Running model: {model_name}")
        print(f"{'='*60}")
        arm = run_model_arm(
            model_name=model_name,
            candidate_summary=candidate_summary,
            context_pack=context_pack,
            prompt_template=prompt_template,
            run_dir=run_dir / model_name.replace(":", "_"),
            recording_id=args.recording_id,
            candidate_run=args.candidate_run,
            context_run=args.context_run,
        )
        arm_summaries.append(arm)
        print(json.dumps(arm_metric_row(arm), indent=2))

    comparison = build_comparison(arm_summaries, baseline_summary, args)
    write_json(run_dir / "comparison.json", comparison)

    report = build_report(comparison, arm_summaries, baseline_summary)
    (run_dir / "comparison.md").write_text(report, encoding="utf-8")

    summary = {
        "experiment_id": experiment_id,
        "recording_id": args.recording_id,
        "run_dir": str(run_dir),
        "arms": arm_summaries,
        "comparison": comparison,
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "summary.json", summary)
    print(f"\n{'='*60}")
    print(f"Experiment complete: {run_dir}")
    print(f"{'='*60}")
    print(json.dumps(comparison["model_metrics"], indent=2))


def run_model_arm(
    model_name: str,
    candidate_summary: dict[str, Any],
    context_pack: dict[str, Any],
    prompt_template: str,
    run_dir: Path,
    recording_id: int,
    candidate_run: str,
    context_run: str,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    # claude-opus-4-7 does not accept the temperature parameter (it is deprecated for that model)
    kwargs: dict[str, Any] = {"model": model_name, "max_tokens": 4096}
    if not model_name.startswith("claude-opus-4-7"):
        kwargs["temperature"] = 0
    model = ChatAnthropic(**kwargs)  # type: ignore[call-arg]

    arm_start = time.monotonic()
    slice_summaries: list[dict[str, Any]] = []
    promoted: list[dict[str, Any]] = []
    invalid_slice_count = 0
    fence_strip_count = 0
    total_latency_s = 0.0

    for source_slice in candidate_summary["slices"]:
        slice_id = source_slice["slice_id"]
        evidence = add_candidate_ids(slice_id, source_slice.get("evidence", []))
        if not evidence:
            continue

        slice_dir = run_dir / slice_id
        slice_dir.mkdir(parents=True, exist_ok=True)

        prompt = (
            prompt_template.replace("{{ slice_id }}", slice_id)
            .replace("{{ context_pack }}", json.dumps(context_pack, indent=2, ensure_ascii=False))
            .replace("{{ candidate_evidence }}", json.dumps(evidence, indent=2, ensure_ascii=False))
        )
        (slice_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        slice_start = time.monotonic()
        response = model.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=prompt),
            ]
        )
        slice_latency = time.monotonic() - slice_start
        total_latency_s += slice_latency

        raw_content = str(response.content)
        (slice_dir / "raw_response.txt").write_text(raw_content, encoding="utf-8")

        needed_fence_strip = raw_content.strip().startswith("```")
        if needed_fence_strip:
            fence_strip_count += 1

        raw_output = parse_model_json(raw_content)
        normalized = normalize_output(raw_output, slice_id)
        validation = validate_output(normalized, evidence)

        if not validation["valid_shape"]:
            invalid_slice_count += 1

        write_json(slice_dir / "raw_output.json", raw_output)
        write_json(slice_dir / "normalized_output.json", normalized)
        write_json(slice_dir / "validation.json", validation)
        write_json(slice_dir / "timing.json", {"latency_s": round(slice_latency, 3), "model": model_name})

        promoted_items = [
            item
            for item in normalized["classifications"]
            if item["classification"] == "post_meeting_follow_up" and item["promote_to_action_item"]
        ]
        promoted.extend(promoted_items)

        hard_negative_promotions = [item["candidate_id"] for item in promoted_items if item["candidate_id"] in HARD_NEGATIVE_IDS]

        slice_summaries.append(
            {
                "slice_id": slice_id,
                "candidate_count": len(evidence),
                "classification_count": len(normalized["classifications"]),
                "promoted_count": len(promoted_items),
                "hard_negative_promotion_count": len(hard_negative_promotions),
                "hard_negative_promotions": hard_negative_promotions,
                "valid_shape": validation["valid_shape"],
                "complete_candidate_coverage": validation["complete_candidate_coverage"],
                "missing_candidate_ids": validation["missing_candidate_ids"],
                "extra_candidate_ids": validation["extra_candidate_ids"],
                "duplicate_candidate_ids": validation["duplicate_candidate_ids"],
                "latency_s": round(slice_latency, 3),
                "needed_fence_strip": needed_fence_strip,
                "warnings": validation["warnings"],
                "classifications": normalized["classifications"],
            }
        )

        status = "ok" if validation["valid_shape"] else "INVALID"
        print(
            f"  {slice_id}: {len(promoted_items)} promoted, "
            f"coverage={'ok' if validation['complete_candidate_coverage'] else 'MISSING'}, "
            f"fences={'yes' if needed_fence_strip else 'no'}, "
            f"latency={slice_latency:.1f}s [{status}]"
        )

    total_latency_s = time.monotonic() - arm_start

    arm_summary = {
        "model_name": model_name,
        "provider": "anthropic",
        "run_dir": str(run_dir),
        "candidate_run": candidate_run,
        "context_run": context_run,
        "slice_count": len(slice_summaries),
        "invalid_slice_count": invalid_slice_count,
        "promoted_count": len(promoted),
        "promoted": promoted,
        "fence_strip_count": fence_strip_count,
        "total_latency_s": round(total_latency_s, 1),
        "slices": slice_summaries,
    }
    write_json(run_dir / "summary.json", arm_summary)
    return arm_summary


def arm_metric_row(arm: dict[str, Any]) -> dict[str, Any]:
    slices = arm["slices"]
    hard_negative_count = sum(s["hard_negative_promotion_count"] for s in slices)
    coverage_failures = sum(1 for s in slices if not s["complete_candidate_coverage"])
    missing_ids: list[str] = []
    for s in slices:
        missing_ids.extend(s["missing_candidate_ids"])
    return {
        "model": arm["model_name"],
        "promoted_count": arm["promoted_count"],
        "hard_negative_promotions": hard_negative_count,
        "coverage_failures": coverage_failures,
        "missing_candidate_ids": missing_ids,
        "invalid_slice_count": arm["invalid_slice_count"],
        "fence_strip_count": arm["fence_strip_count"],
        "total_latency_s": arm["total_latency_s"],
    }


def build_comparison(
    arm_summaries: list[dict[str, Any]],
    baseline_summary: dict[str, Any] | None,
    args: argparse.Namespace,
) -> dict[str, Any]:
    model_metrics = [arm_metric_row(arm) for arm in arm_summaries]

    baseline_metrics: dict[str, Any] | None = None
    if baseline_summary:
        baseline_slices = baseline_summary.get("slices", [])
        baseline_promoted = baseline_summary.get("promoted", [])
        baseline_hard_neg = sum(
            1 for item in baseline_promoted if item.get("candidate_id") in HARD_NEGATIVE_IDS
        )
        baseline_coverage_failures = sum(
            1 for s in baseline_slices if not s.get("complete_candidate_coverage", True)
        )
        baseline_missing: list[str] = []
        for s in baseline_slices:
            baseline_missing.extend(s.get("missing_candidate_ids", []))
        baseline_metrics = {
            "model": "gemma4:e2b (repaired baseline)",
            "promoted_count": baseline_summary.get("promoted_count", len(baseline_promoted)),
            "hard_negative_promotions": baseline_hard_neg,
            "coverage_failures": baseline_coverage_failures,
            "missing_candidate_ids": baseline_missing,
            "invalid_slice_count": baseline_summary.get("invalid_slice_count", 0),
            "fence_strip_count": 0,
            "total_latency_s": None,
        }

    return {
        "candidate_run": args.candidate_run,
        "context_run": args.context_run,
        "baseline_run": args.baseline_run or None,
        "model_metrics": model_metrics,
        "baseline_metrics": baseline_metrics,
    }


def build_report(
    comparison: dict[str, Any],
    arm_summaries: list[dict[str, Any]],
    baseline_summary: dict[str, Any] | None,
) -> str:
    lines = [
        "# Claude Model Comparison: Action Items V4 Context Classifier",
        "",
        "## Purpose",
        "",
        "Compare `claude-sonnet-4-6` and `claude-opus-4-7` against the `gemma4:e2b` V4 repaired baseline.",
        "Same prompt (`prompt_v4_context_classifier.md`), same candidate and context pack inputs.",
        "",
        f"- Candidate run: `{comparison['candidate_run']}`",
        f"- Context run: `{comparison['context_run']}`",
        f"- Baseline run: `{comparison['baseline_run'] or '(not provided)'}`",
        "",
        "## Model Comparison Table",
        "",
        "| Model | Promoted | Hard-Neg Promoted | Coverage Failures | Missing IDs | Invalid Slices | Fence Strips | Latency (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    def row(m: dict[str, Any]) -> str:
        lat = f"{m['total_latency_s']:.1f}" if m["total_latency_s"] is not None else "N/A (repaired)"
        return (
            f"| {m['model']} "
            f"| {m['promoted_count']} "
            f"| {m['hard_negative_promotions']} "
            f"| {m['coverage_failures']} "
            f"| {len(m['missing_candidate_ids'])} "
            f"| {m['invalid_slice_count']} "
            f"| {m['fence_strip_count']} "
            f"| {lat} |"
        )

    if comparison["baseline_metrics"]:
        lines.append(row(comparison["baseline_metrics"]))
    for m in comparison["model_metrics"]:
        lines.append(row(m))

    lines += [
        "",
        "## Per-Slice Detail",
        "",
    ]

    for arm in arm_summaries:
        lines.append(f"### {arm['model_name']}")
        lines.append("")
        lines.append("| Slice | Candidates | Promoted | Hard-Neg | Coverage | Fences | Latency (s) |")
        lines.append("| --- | ---: | ---: | ---: | --- | --- | ---: |")
        for s in arm["slices"]:
            coverage = "ok" if s["complete_candidate_coverage"] else f"MISSING {s['missing_candidate_ids']}"
            lines.append(
                f"| {s['slice_id']} "
                f"| {s['candidate_count']} "
                f"| {s['promoted_count']} "
                f"| {s['hard_negative_promotion_count']} "
                f"| {coverage} "
                f"| {'yes' if s['needed_fence_strip'] else 'no'} "
                f"| {s['latency_s']:.1f} |"
            )
        lines.append("")

    lines += [
        "## Promoted Candidates",
        "",
    ]
    for arm in arm_summaries:
        lines.append(f"### {arm['model_name']}")
        lines.append("")
        if not arm["promoted"]:
            lines.append("No candidates promoted.")
        else:
            lines.append("| Time | Speaker | Excerpt | classification_reason |")
            lines.append("| --- | --- | --- | --- |")
            for item in arm["promoted"]:
                excerpt = item.get("excerpt", "").replace("|", "\\|")
                reason = item.get("classification_reason", "").replace("|", "\\|")
                lines.append(
                    f"| {item.get('timestamp', '')} "
                    f"| {item.get('speaker', '')} "
                    f"| {excerpt[:80]}{'…' if len(excerpt) > 80 else ''} "
                    f"| {reason[:60]}{'…' if len(reason) > 60 else ''} |"
                )
        lines.append("")

    lines += [
        "## Interpretation Notes",
        "",
        "*(Fill in after reviewing results.)*",
        "",
        "### Coverage",
        "",
        "- Did cloud models require repair passes for missing candidates?",
        "- Compare to gemma4 which needed repair on 2 of 6 candidate-bearing slices.",
        "",
        "### Precision",
        "",
        "- How many hard-negative candidates were promoted?",
        "- Compare to gemma4 repaired baseline (0 hard-negative promotions after repair).",
        "",
        "### JSON compliance",
        "",
        "- Did either model add markdown fences despite explicit instructions?",
        "- Note fence_strip_count per model.",
        "",
        "### Latency",
        "",
        "- Total wall-clock per model (cloud latency is per-slice, not local inference).",
        "",
        "### Sonnet vs Opus",
        "",
        "- Record any differences in reasoning quality, coverage compliance, or precision.",
        "- Note whether Opus improvements justify the cost difference for this task.",
        "",
        "## Recommended Next Step",
        "",
        "*(Fill in after reviewing results.)*",
    ]

    return "\n".join(lines) + "\n"


def parse_model_json(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        try:
            return json.loads("\n".join(lines))
        except json.JSONDecodeError:
            pass

    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass

    return {"target": "action_items_context_classifier", "classifications": [], "parse_warning": "invalid_json"}


def normalize_output(payload: Any, slice_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"target": "action_items_context_classifier", "slice_id": slice_id, "classifications": []}
    classifications = payload.get("classifications", [])
    if not isinstance(classifications, list):
        classifications = []
    return {
        "target": str(payload.get("target") or "action_items_context_classifier"),
        "slice_id": str(payload.get("slice_id") or slice_id),
        "classifications": [item for item in (normalize_classification(item) for item in classifications) if item],
    }


def normalize_classification(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    classification = str(item.get("classification", "")).strip()
    if classification not in {
        "post_meeting_follow_up",
        "in_meeting_action",
        "role_or_ownership_statement",
        "not_action_item",
    }:
        classification = "not_action_item"
    promote = bool(item.get("promote_to_action_item")) and classification == "post_meeting_follow_up"
    return {
        "candidate_id": str(item.get("candidate_id", "")).strip(),
        "speaker": str(item.get("speaker", "")).strip(),
        "timestamp": str(item.get("timestamp", "")).strip(),
        "excerpt": str(item.get("excerpt", "")).strip(),
        "classification": classification,
        "owner": item.get("owner"),
        "promote_to_action_item": promote,
        "classification_reason": str(item.get("classification_reason", "")).strip(),
    }


def validate_output(output: dict[str, Any], input_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    warnings = []
    if output["target"] != "action_items_context_classifier":
        warnings.append("unexpected target field")
    expected_ids = [item["candidate_id"] for item in input_evidence]
    actual_ids = [item["candidate_id"] for item in output["classifications"] if item["candidate_id"]]
    missing_ids = sorted(set(expected_ids) - set(actual_ids))
    extra_ids = sorted(set(actual_ids) - set(expected_ids))
    duplicate_ids = sorted({cid for cid in actual_ids if actual_ids.count(cid) > 1})
    if missing_ids:
        warnings.append(f"missing candidate classifications: {missing_ids}")
    if extra_ids:
        warnings.append(f"unknown candidate classifications: {extra_ids}")
    if duplicate_ids:
        warnings.append(f"duplicate candidate classifications: {duplicate_ids}")
    for index, item in enumerate(output["classifications"]):
        if not item["candidate_id"]:
            warnings.append(f"classification {index} missing candidate_id")
        if not item["speaker"] or not item["timestamp"] or not item["excerpt"]:
            warnings.append(f"classification {index} missing evidence fields")
        if item["promote_to_action_item"] and item["classification"] != "post_meeting_follow_up":
            warnings.append(f"classification {index} has invalid promotion")
    return {
        "valid_shape": not warnings,
        "complete_candidate_coverage": not missing_ids and not extra_ids and not duplicate_ids,
        "expected_candidate_count": len(expected_ids),
        "actual_candidate_count": len(actual_ids),
        "missing_candidate_ids": missing_ids,
        "extra_candidate_ids": extra_ids,
        "duplicate_candidate_ids": duplicate_ids,
        "warnings": warnings,
    }


def add_candidate_ids(slice_id: str, evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for index, item in enumerate(evidence, start=1):
        candidate = dict(item)
        candidate["candidate_id"] = f"{slice_id}_candidate_{index:02d}"
        result.append(candidate)
    return result


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
