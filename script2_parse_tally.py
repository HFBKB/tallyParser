#!/usr/bin/env python3
# script2_parse_tally.py
import json
import os
import re
import argparse
from datetime import datetime
from typing import Any, Dict, List, Union
import yaml
from pathlib import Path

# -----------------------
# Helpers
# -----------------------
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")

def load_yaml(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, obj: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def try_convert_number(s: str) -> Union[int, float, str]:
    if isinstance(s, (int, float)):
        return s
    if not isinstance(s, str):
        return s
    if NUM_RE.match(s.strip()):
        if "." in s:
            try:
                return float(s)
            except ValueError:
                return s
        else:
            try:
                return int(s)
            except ValueError:
                return s
    return s

def try_parse_date(s: str) -> str:
    # Try common ISO-like formats, return ISO date/time string on success
    if not isinstance(s, str):
        return s
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.isoformat()
        except Exception:
            continue
    return s

def set_nested(d: Dict, keys: List[str], value: Any, keep_empty: bool):
    cur = d
    for k in keys[:-1]:
        if k not in cur or not isinstance(cur[k], dict):
            cur[k] = {}
        cur = cur[k]
    last = keys[-1]
    if value is None and not keep_empty:
        return
    cur[last] = value

# -----------------------
# Normalization logic
# -----------------------
def normalize_answer(title: str,
                     answer: Any,
                     qtype: str,
                     cfg: Dict[str, Any]) -> Any:
    """
    - Unwrap single-item lists if configured.
    - Convert numeric strings to numbers if configured.
    - Parse dates to ISO if configured.
    - Keep file-upload lists intact (heuristic: dicts with 'url' or 'name').
    """
    if answer is None:
        return None

    # Detect file upload objects: list of dicts with 'url' or 'name'
    if isinstance(answer, list) and answer and isinstance(answer[0], dict):
        if any(k in answer[0] for k in ("url", "name", "filename")):
            return answer

    # If list and unwrap_single_item_lists -> maybe unwrap
    if isinstance(answer, list):
        if cfg.get("parsing", {}).get("unwrap_single_item_lists", True) and len(answer) == 1:
            answer = answer[0]
        else:
            # normalize each element
            return [normalize_answer(title, a, qtype, cfg) for a in answer]

    # Convert numeric strings
    if cfg.get("parsing", {}).get("convert_numeric_strings", True):
        if isinstance(answer, str):
            conv = try_convert_number(answer)
            answer = conv

    # Parse dates
    if cfg.get("parsing", {}).get("parse_dates_iso", True):
        # Heuristic: if qtype mentions DATE or title contains 'date' or value matches date patterns
        if isinstance(answer, str) and ("date" in (qtype or "").lower() or "date" in (title or "").lower()):
            parsed = try_parse_date(answer)
            answer = parsed

    return answer

# -----------------------
# Build question map
# -----------------------
def build_question_map(raw: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    qmap: Dict[str, Dict[str, Any]] = {}
    for q in raw.get("questions", []):
        qid = q.get("id")
        title = q.get("title")
        qtype = q.get("type")
        fields = q.get("fields") or []
        if fields and fields[0].get("title"):
            title = fields[0].get("title")
        if qid:
            qmap[qid] = {"title": title, "type": qtype}
    return qmap

# -----------------------
# Parse single submission
# -----------------------
def parse_submission(raw: Dict[str, Any], submission: Dict[str, Any], qmap: Dict[str, Dict[str, Any]], cfg: Dict[str, Any]) -> Dict[str, Any]:
    parsed = {
        "submissionId": submission.get("id"),
        "formId": submission.get("formId"),
        "respondentId": submission.get("respondentId"),
        "submittedAt": submission.get("submittedAt"),
        "data": {}
    }
    for resp in submission.get("responses", []):
        qid = resp.get("questionId")
        if not qid:
            continue
        meta = qmap.get(qid, {})
        title = meta.get("title") or resp.get("questionId")
        qtype = meta.get("type") or resp.get("questionType") or ""
        answer = resp.get("answer")
        norm = normalize_answer(title, answer, qtype, cfg)
        keys = title.split("|") if isinstance(title, str) else [title]
        set_nested(parsed["data"], keys, norm, cfg.get("parsing", {}).get("keep_empty_keys", False))
    return parsed

# -----------------------
# Main
# -----------------------
def main():
    parser = argparse.ArgumentParser(description="Script2: parse raw Tally submission JSON into normalized JSON")
    parser.add_argument("--config", "-c", default="config/script2.yaml", help="Path to YAML config")
    args = parser.parse_args()

    cfg_path = args.config
    cfg = load_yaml(cfg_path) if Path(cfg_path).exists() else {}
    raw_path = cfg.get("tally", {}).get("input_path", "data/raw_submission.json")
    out_dir = cfg.get("output", {}).get("out_dir", "data/parsed")
    write_agg = cfg.get("output", {}).get("write_aggregated", True)

    ensure_dir(out_dir)
    raw = load_json(raw_path)
    qmap = build_question_map(raw)
    submissions = raw.get("submissions", []) or raw.get("items", []) or []

    all_parsed = []
    for sub in submissions:
        parsed = parse_submission(raw, sub, qmap, cfg)
        all_parsed.append(parsed)
        sid = parsed.get("submissionId") or parsed.get("respondentId") or "unknown"
        out_file = os.path.join(out_dir, f"submission_{sid}.json")
        write_json(out_file, parsed)
        print(f"Wrote {out_file}")

    if write_agg:
        agg_path = os.path.join(out_dir, "all_submissions_parsed.json")
        write_json(agg_path, all_parsed)
        print(f"Wrote aggregated file {agg_path}")

if __name__ == "__main__":
    main()
