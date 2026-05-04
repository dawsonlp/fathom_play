"""Classify action-item candidates using a local context pack.

This runner uses only local experiment artifacts. It does not call Fathom.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

ROOT = Path(__file__).resolve().parent
RUNS_DIR = ROOT / "runs"
PROMPT_PATH = ROOT / "targets" / "action_items" / "prompt_v4_context_classifier.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify action-item candidates using local context pack.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--candidate-run", required=True, help="V2 candidate source run ID")
    parser.add_argument("--context-run", required=True, help="Context preprocessing run ID")
    args = parser.parse_args()

    candidate_dir = RUNS_DIR / str(args.recording_id) / args.candidate_run
    context_dir = RUNS_DIR / str(args.recording_id) / args.context_run
    if not candidate_dir.exists():
        raise SystemExit(f"Candidate run not found: {candidate_dir}")
    if not context_dir.exists():
        raise SystemExit(f"Context run not found: {context_dir}")

    candidate_summary = read_json(candidate_dir / "summary.json")
    context_pack = read_json(context_dir / "deterministic_context_pack.json")

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"action_items-v4-context-classifier-{args.recording_id}-{timestamp}"
    run_dir = RUNS_DIR / str(args.recording_id) / experiment_id
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
            "prompt_path": str(PROMPT_PATH.relative_to(ROOT)),
            "model": {"provider": "ollama", "name": "gemma4:e2b", "format": "json", "temperature": 0},
            "created_at": datetime.now(UTC).isoformat(),
            "uses_fathom_api": False,
        },
    )

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    model = ChatOllama(model="gemma4:e2b", format="json", temperature=0)
    slice_summaries = []
    promoted = []
    invalid_slice_count = 0

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

        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        "You classify action-item candidates using a compact context pack. "
                        "Return only valid JSON and obey the hard negative rules."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        raw_output = parse_model_json(str(response.content))
        normalized = normalize_output(raw_output, slice_id)
        validation = validate_output(normalized, evidence)
        if not validation["valid_shape"]:
            invalid_slice_count += 1

        write_json(slice_dir / "raw_output.json", raw_output)
        write_json(slice_dir / "normalized_output.json", normalized)
        write_json(slice_dir / "validation.json", validation)

        promoted_items = [
            item
            for item in normalized["classifications"]
            if item["classification"] == "post_meeting_follow_up" and item["promote_to_action_item"]
        ]
        promoted.extend(promoted_items)
        slice_summaries.append(
            {
                "slice_id": slice_id,
                "candidate_count": len(evidence),
                "classification_count": len(normalized["classifications"]),
                "promoted_count": len(promoted_items),
                "valid_shape": validation["valid_shape"],
                "complete_candidate_coverage": validation["complete_candidate_coverage"],
                "missing_candidate_ids": validation["missing_candidate_ids"],
                "extra_candidate_ids": validation["extra_candidate_ids"],
                "duplicate_candidate_ids": validation["duplicate_candidate_ids"],
                "warnings": validation["warnings"],
                "classifications": normalized["classifications"],
            }
        )

    summary = {
        "experiment_id": experiment_id,
        "candidate_run": args.candidate_run,
        "context_run": args.context_run,
        "run_dir": str(run_dir),
        "slice_count": len(slice_summaries),
        "invalid_slice_count": invalid_slice_count,
        "promoted_count": len(promoted),
        "promoted": promoted,
        "slices": slice_summaries,
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def parse_model_json(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(content[start : end + 1])
        except json.JSONDecodeError:
            pass
    return {"target": "action_items_context_classifier", "classifications": []}


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
        warnings.append("unexpected target")
    expected_ids = [item["candidate_id"] for item in input_evidence]
    actual_ids = [item["candidate_id"] for item in output["classifications"] if item["candidate_id"]]
    missing_ids = sorted(set(expected_ids) - set(actual_ids))
    extra_ids = sorted(set(actual_ids) - set(expected_ids))
    duplicate_ids = sorted({candidate_id for candidate_id in actual_ids if actual_ids.count(candidate_id) > 1})
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
