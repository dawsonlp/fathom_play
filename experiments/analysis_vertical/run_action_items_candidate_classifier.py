"""Classify V2 action-item evidence candidates."""

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
PROMPT_PATH = ROOT / "targets" / "action_items" / "prompt_v3_candidate_classifier.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify V2 action-item evidence candidates.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    parser.add_argument("--source-run", required=True, help="V2 source experiment ID")
    args = parser.parse_args()

    source_dir = RUNS_DIR / str(args.recording_id) / args.source_run
    if not source_dir.exists():
        raise SystemExit(f"Source run not found: {source_dir}")

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"action_items-v3-classifier-{args.recording_id}-{timestamp}"
    run_dir = RUNS_DIR / str(args.recording_id) / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    source_summary = read_json(source_dir / "summary.json")
    manifest = {
        "experiment_id": experiment_id,
        "recording_id": args.recording_id,
        "target": "action_items",
        "vertical_variant": "v3_candidate_classifier",
        "source_run": args.source_run,
        "prompt_path": str(PROMPT_PATH.relative_to(ROOT)),
        "model": {"provider": "ollama", "name": "gemma4:e2b", "format": "json", "temperature": 0},
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "manifest.json", manifest)

    prompt_template = PROMPT_PATH.read_text(encoding="utf-8")
    model = ChatOllama(model="gemma4:e2b", format="json", temperature=0)
    slice_summaries = []
    promoted = []

    for source_slice in source_summary["slices"]:
        evidence = source_slice.get("evidence", [])
        if not evidence:
            continue

        slice_id = source_slice["slice_id"]
        slice_dir = run_dir / slice_id
        slice_dir.mkdir(parents=True, exist_ok=True)
        prompt = (
            prompt_template.replace("{{ slice_id }}", slice_id).replace(
                "{{ candidate_evidence }}", json.dumps(evidence, indent=2, ensure_ascii=False)
            )
        )
        (slice_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        response = model.invoke(
            [
                SystemMessage(
                    content=(
                        "You classify candidate action-item evidence. "
                        "Return only valid JSON and preserve the supplied evidence text."
                    )
                ),
                HumanMessage(content=prompt),
            ]
        )
        raw_output = parse_model_json(str(response.content))
        normalized = normalize_output(raw_output, slice_id)
        validation = validate_output(normalized)

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
                "warnings": validation["warnings"],
                "classifications": normalized["classifications"],
            }
        )

    summary = {
        "experiment_id": experiment_id,
        "source_run": args.source_run,
        "run_dir": str(run_dir),
        "slice_count": len(slice_summaries),
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
    return {"target": "action_items_candidate_classification", "classifications": []}


def normalize_output(payload: Any, slice_id: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {"target": "action_items_candidate_classification", "slice_id": slice_id, "classifications": []}
    classifications = payload.get("classifications", [])
    if not isinstance(classifications, list):
        classifications = []
    return {
        "target": str(payload.get("target") or "action_items_candidate_classification"),
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
        "speaker": str(item.get("speaker", "")).strip(),
        "timestamp": str(item.get("timestamp", "")).strip(),
        "excerpt": str(item.get("excerpt", "")).strip(),
        "candidate_reason": str(item.get("candidate_reason", "")).strip(),
        "classification": classification,
        "owner": item.get("owner"),
        "promote_to_action_item": promote,
        "classification_reason": str(item.get("classification_reason", "")).strip(),
    }


def validate_output(output: dict[str, Any]) -> dict[str, Any]:
    warnings = []
    if output["target"] != "action_items_candidate_classification":
        warnings.append("unexpected target")
    for index, item in enumerate(output["classifications"]):
        if not item["speaker"] or not item["timestamp"] or not item["excerpt"]:
            warnings.append(f"classification {index} missing evidence fields")
        if item["promote_to_action_item"] and item["classification"] != "post_meeting_follow_up":
            warnings.append(f"classification {index} has invalid promotion")
    return {"valid_shape": not warnings, "warnings": warnings}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
