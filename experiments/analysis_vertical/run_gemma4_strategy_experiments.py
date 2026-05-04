"""Run three local Gemma4 strategy experiments.

The experiments use only local artifacts:

1. Prompt shape and reasoning matrix.
2. Context composition and reasoning matrix.
3. Candidate-to-final synthesis for action items and significant ideas.
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

ACTION_CANDIDATE_RUN = "action_items-v2-slices-140341999-20260503-022458"
CONTEXT_RUN = "context_pack-v1-140341999-20260503-030135"
REPAIRED_RUN = "action_items-v4-repaired-140341999-20260503-165550"
SIGNIFICANT_IDEAS_RUN = "significant_ideas-v1-slices-140341999-20260503-023715"

HARD_NEGATIVE_IDS = {
    "slice_01_00:00_05:00_candidate_01",
    "slice_01_00:00_05:00_candidate_02",
    "slice_03_10:00_15:00_candidate_01",
    "slice_08_35:00_40:00_candidate_01",
    "slice_08_35:00_40:00_candidate_02",
    "slice_09_40:00_45:00_candidate_01",
    "slice_09_40:00_45:00_candidate_02",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Gemma4 strategy experiments.")
    parser.add_argument("--recording-id", type=int, default=140341999)
    args = parser.parse_args()

    root = RUNS_DIR / str(args.recording_id)
    action_candidates = load_action_candidates(root / ACTION_CANDIDATE_RUN / "summary.json")
    context_pack = read_json(root / CONTEXT_RUN / "deterministic_context_pack.json")
    repaired = read_json(root / REPAIRED_RUN / "summary.json")
    significant_ideas = read_json(root / SIGNIFICANT_IDEAS_RUN / "summary.json")

    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    experiment_id = f"gemma4-strategy-experiments-{args.recording_id}-{timestamp}"
    run_dir = root / experiment_id
    run_dir.mkdir(parents=True, exist_ok=True)

    experiment_1 = run_prompt_shape_matrix(action_candidates, context_pack, run_dir / "experiment_1_prompt_shape")
    experiment_2 = run_context_composition_matrix(action_candidates, context_pack, run_dir / "experiment_2_context")
    experiment_3 = run_synthesis_experiment(
        action_candidates,
        context_pack,
        repaired,
        significant_ideas,
        run_dir / "experiment_3_synthesis",
    )

    summary = {
        "experiment_id": experiment_id,
        "recording_id": args.recording_id,
        "run_dir": str(run_dir),
        "experiments": {
            "prompt_shape_reasoning": experiment_1,
            "context_composition": experiment_2,
            "iterative_synthesis": experiment_3,
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    write_json(run_dir / "summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def run_prompt_shape_matrix(
    candidates: list[dict[str, Any]], context_pack: dict[str, Any], output_dir: Path
) -> list[dict[str, Any]]:
    variants = {
        "full_rules": classifier_prompt(candidates, context_pack, style="full"),
        "short_rules": classifier_prompt(candidates, context_pack, style="short"),
        "two_phase": classifier_prompt(candidates, context_pack, style="two_phase"),
    }
    results = []
    for variant, prompt in variants.items():
        for reasoning in (False, True):
            results.append(
                run_classifier_case(
                    output_dir=output_dir / f"{variant}_{reasoning_label(reasoning)}",
                    prompt=prompt,
                    candidates=candidates,
                    variant=variant,
                    context_variant="full_context",
                    reasoning=reasoning,
                )
            )
    return results


def run_context_composition_matrix(
    candidates: list[dict[str, Any]], context_pack: dict[str, Any], output_dir: Path
) -> list[dict[str, Any]]:
    context_variants = {
        "no_context": {},
        "mechanics_only": {"meeting_mechanics": context_pack.get("meeting_mechanics", [])},
        "significant_only": {
            "meeting_purpose": context_pack.get("meeting_purpose", ""),
            "core_ideas": context_pack.get("core_ideas", []),
            "strategic_intentions": context_pack.get("strategic_intentions", []),
        },
        "mechanics_plus_significant": {
            "meeting_purpose": context_pack.get("meeting_purpose", ""),
            "core_ideas": context_pack.get("core_ideas", []),
            "meeting_mechanics": context_pack.get("meeting_mechanics", []),
            "downstream_guidance": context_pack.get("downstream_guidance", []),
        },
        "full_context": context_pack,
        "ultra_compact": {
            "meeting_purpose": context_pack.get("meeting_purpose", ""),
            "noise": "Screen sharing, slide navigation, hard stops, and travel talk are not action items.",
            "action_rule": "Promote only post-meeting tasks with concrete outside-meeting work.",
        },
    }
    results = []
    for variant, context in context_variants.items():
        prompt = classifier_prompt(candidates, context, style="short")
        for reasoning in (False, True):
            results.append(
                run_classifier_case(
                    output_dir=output_dir / f"{variant}_{reasoning_label(reasoning)}",
                    prompt=prompt,
                    candidates=candidates,
                    variant="short_rules",
                    context_variant=variant,
                    reasoning=reasoning,
                )
            )
    return results


def run_synthesis_experiment(
    candidates: list[dict[str, Any]],
    context_pack: dict[str, Any],
    repaired: dict[str, Any],
    significant_ideas: dict[str, Any],
    output_dir: Path,
) -> list[dict[str, Any]]:
    action_promoted = repaired["promoted"]
    idea_evidence = [
        evidence
        for item in significant_ideas["slices"]
        for evidence in item.get("evidence", [])
        if evidence.get("idea_type") not in {"personal_context", "logistics_update"}
    ]
    cases = {
        "action_items_final": final_action_prompt(action_promoted, context_pack),
        "action_items_all_candidates": final_action_prompt(candidates, context_pack),
        "significant_ideas_final": final_ideas_prompt(idea_evidence, context_pack),
    }
    results = []
    for name, prompt in cases.items():
        for reasoning in (False, True):
            case_dir = output_dir / f"{name}_{reasoning_label(reasoning)}"
            response = run_model(prompt, reasoning)
            parsed = parse_model_json(response["content"])
            write_case(case_dir, prompt, parsed, response["reasoning_content"])
            results.append(
                {
                    "case": name,
                    "reasoning": reasoning,
                    "valid_json": isinstance(parsed, dict),
                    "top_level_keys": sorted(parsed.keys()) if isinstance(parsed, dict) else [],
                    "item_count": count_synthesis_items(parsed),
                    "has_parse_warning": isinstance(parsed, dict) and "parse_warning" in parsed,
                    "output_dir": str(case_dir),
                }
            )
    return results


def run_classifier_case(
    output_dir: Path,
    prompt: str,
    candidates: list[dict[str, Any]],
    variant: str,
    context_variant: str,
    reasoning: bool,
) -> dict[str, Any]:
    response = run_model(prompt, reasoning)
    parsed = parse_model_json(response["content"])
    normalized = normalize_classifier(parsed)
    validation = validate_classifications(normalized["classifications"], candidates)
    promotions = [
        item
        for item in normalized["classifications"]
        if item["classification"] == "post_meeting_follow_up" and item["promote_to_action_item"]
    ]
    hard_negative_promotions = [
        item["candidate_id"] for item in promotions if item["candidate_id"] in HARD_NEGATIVE_IDS
    ]
    write_case(
        output_dir,
        prompt,
        {
            "raw_output": parsed,
            "normalized": normalized,
            "validation": validation,
            "promotions": promotions,
            "hard_negative_promotions": hard_negative_promotions,
        },
        response["reasoning_content"],
    )
    return {
        "variant": variant,
        "context_variant": context_variant,
        "reasoning": reasoning,
        "valid_shape": validation["valid_shape"],
        "complete_candidate_coverage": validation["complete_candidate_coverage"],
        "missing_count": len(validation["missing_candidate_ids"]),
        "extra_count": len(validation["extra_candidate_ids"]),
        "duplicate_count": len(validation["duplicate_candidate_ids"]),
        "promotion_count": len(promotions),
        "hard_negative_promotion_count": len(hard_negative_promotions),
        "hard_negative_promotions": hard_negative_promotions,
        "output_dir": str(output_dir),
    }


def classifier_prompt(candidates: list[dict[str, Any]], context: dict[str, Any], style: str) -> str:
    if style == "short":
        instructions = (
            "Classify every candidate_id exactly once. Promote only concrete post-meeting tasks. "
            "Reject screen sharing, slide presentation/navigation, hard stops, vague statements, and role ownership."
        )
    elif style == "two_phase":
        instructions = (
            "Step 1: classify every candidate_id exactly once. "
            "Step 2: set promote_to_action_item true only for post_meeting_follow_up items that are concrete tasks. "
            "The final JSON must include only the classifications array, not your notes."
        )
    else:
        instructions = (
            "Classify each candidate. Only promote true post-meeting follow-up tasks. "
            "Hard negatives: screen sharing, testing meeting technology, walking through slides, paging slides, "
            "skipping forward, showing material during the meeting, hard stops, time remaining, and general ownership "
            "statements are not promoted action items. The words I will, I'll, or we'll are not enough."
        )
    return f"""
Return only JSON:
{{
  "target": "action_items_context_classifier",
  "classifications": [
    {{
      "candidate_id": "candidate id",
      "speaker": "speaker name",
      "timestamp": "MM:SS",
      "excerpt": "exact candidate excerpt",
      "classification": "post_meeting_follow_up|in_meeting_action|role_or_ownership_statement|not_action_item",
      "owner": "person name or null",
      "promote_to_action_item": false,
      "classification_reason": "brief reason"
    }}
  ]
}}

Instructions:
{instructions}

Context:
{json.dumps(context, indent=2, ensure_ascii=False)}

Candidates:
{json.dumps(candidates, indent=2, ensure_ascii=False)}
"""


def final_action_prompt(items: list[dict[str, Any]], context_pack: dict[str, Any]) -> str:
    return f"""
Create final action items from the supplied candidate classifications.

Rules:
- Return only JSON.
- Include only concrete post-meeting tasks.
- Use null when owner or task detail is unclear.
- Preserve evidence candidate_ids.
- If candidates are too vague, exclude them and explain why in excluded_items.

JSON shape:
{{
  "target": "final_action_items",
  "action_items": [
    {{
      "task": "specific task",
      "owner": "person or null",
      "evidence_candidate_ids": ["id"],
      "confidence": "high|medium|low"
    }}
  ],
  "excluded_items": [
    {{"candidate_id": "id", "reason": "why excluded"}}
  ]
}}

Context:
{json.dumps(context_pack, indent=2, ensure_ascii=False)}

Candidates:
{json.dumps(items, indent=2, ensure_ascii=False)}
"""


def final_ideas_prompt(evidence: list[dict[str, Any]], context_pack: dict[str, Any]) -> str:
    return f"""
Synthesize significant meeting ideas from evidence candidates.

Rules:
- Return only JSON.
- Group related evidence into succinct ideas.
- Do not add facts not supported by evidence.
- Preserve supporting timestamps.
- Exclude logistics/travel/screen sharing.

JSON shape:
{{
  "target": "significant_ideas_synthesis",
  "ideas": [
    {{
      "idea": "succinct idea",
      "category": "intention|proposal|principle|design_direction|strategic_concern|assumption",
      "supporting_timestamps": ["MM:SS"],
      "confidence": "high|medium|low"
    }}
  ],
  "excluded_items": [
    {{"timestamp": "MM:SS", "reason": "why excluded"}}
  ]
}}

Context:
{json.dumps(context_pack, indent=2, ensure_ascii=False)}

Evidence:
{json.dumps(evidence, indent=2, ensure_ascii=False)}
"""


def run_model(prompt: str, reasoning: bool) -> dict[str, str]:
    model = ChatOllama(model="gemma4:e2b", format="json", temperature=0, reasoning=reasoning)
    response = model.invoke(
        [
            SystemMessage(content="Return only valid JSON. Obey all coverage requirements."),
            HumanMessage(content=prompt),
        ]
    )
    return {
        "content": str(response.content),
        "reasoning_content": str(response.additional_kwargs.get("reasoning_content", "")),
    }


def load_action_candidates(path: Path) -> list[dict[str, Any]]:
    summary = read_json(path)
    candidates = []
    for source_slice in summary["slices"]:
        slice_id = source_slice["slice_id"]
        for index, evidence in enumerate(source_slice.get("evidence", []), start=1):
            item = dict(evidence)
            item["candidate_id"] = f"{slice_id}_candidate_{index:02d}"
            item["slice_id"] = slice_id
            candidates.append(item)
    return candidates


def normalize_classifier(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"target": "action_items_context_classifier", "classifications": []}
    classifications = payload.get("classifications", [])
    if not isinstance(classifications, list):
        classifications = []
    return {
        "target": str(payload.get("target") or "action_items_context_classifier"),
        "classifications": [
            item for item in (normalize_classification(item) for item in classifications) if item
        ],
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


def validate_classifications(
    classifications: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> dict[str, Any]:
    expected_ids = [item["candidate_id"] for item in candidates]
    actual_ids = [item["candidate_id"] for item in classifications if item["candidate_id"]]
    missing_ids = sorted(set(expected_ids) - set(actual_ids))
    extra_ids = sorted(set(actual_ids) - set(expected_ids))
    duplicate_ids = sorted({candidate_id for candidate_id in actual_ids if actual_ids.count(candidate_id) > 1})
    return {
        "valid_shape": not missing_ids and not extra_ids and not duplicate_ids,
        "complete_candidate_coverage": not missing_ids and not extra_ids and not duplicate_ids,
        "missing_candidate_ids": missing_ids,
        "extra_candidate_ids": extra_ids,
        "duplicate_candidate_ids": duplicate_ids,
    }


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
    return {"parse_warning": "invalid_json", "raw": content}


def count_synthesis_items(parsed: Any) -> int:
    if not isinstance(parsed, dict):
        return 0
    for key in ("action_items", "ideas", "items"):
        if isinstance(parsed.get(key), list):
            return len(parsed[key])
    return 0


def write_case(output_dir: Path, prompt: str, output: Any, reasoning_content: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    write_json(output_dir / "output.json", output)
    (output_dir / "reasoning.txt").write_text(reasoning_content, encoding="utf-8")


def reasoning_label(reasoning: bool) -> str:
    return "reasoning_on" if reasoning else "reasoning_off"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
