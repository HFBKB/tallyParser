#!/usr/bin/env python3
# script2_parse_tally.py (modifié pour téléchargement automatique des fichiers référencés)
import json
import os
import re
import argparse
from datetime import datetime
from typing import Any, Dict, List, Union, Tuple
import yaml
from pathlib import Path
import requests
import mimetypes
import hashlib
from urllib.parse import urlparse, unquote

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
# Download utilities
# -----------------------
def safe_filename_from_url(url: str) -> str:
    p = urlparse(url)
    name = os.path.basename(unquote(p.path)) or "file"
    # sanitize
    name = re.sub(r'[^A-Za-z0-9._-]', '_', name)
    return name

def ext_from_mimetype(mime: str) -> str:
    if not mime:
        return ""
    ext = mimetypes.guess_extension(mime.split(";")[0].strip())
    return ext or ""

def unique_filename(dest_dir: str, base: str) -> str:
    base_name, base_ext = os.path.splitext(base)
    candidate = base
    i = 1
    while os.path.exists(os.path.join(dest_dir, candidate)):
        candidate = f"{base_name}_{i}{base_ext}"
        i += 1
    return candidate

def hash_url(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]

def download_file(url: str, dest_dir: str, cfg: Dict[str, Any]) -> Tuple[bool, str, str]:
    """
    Télécharge l'URL dans dest_dir si autorisé par cfg.
    Retourne (success, local_path, local_filename).
    """
    try:
        timeout = cfg.get("timeout_seconds", 30)
        r = requests.get(url, stream=True, timeout=timeout)
    except Exception as e:
        return False, "", f"download_error: {e}"

    if r.status_code != 200:
        return False, "", f"http_status_{r.status_code}"

    # taille
    max_size = cfg.get("max_size_bytes", 0)
    content_length = r.headers.get("Content-Length")
    if content_length and max_size and int(content_length) > max_size:
        return False, "", "size_exceeds_limit"

    # déterminer mimetype
    content_type = r.headers.get("Content-Type", "")
    allowed = cfg.get("allowed_mimetypes", []) or []
    if allowed and content_type:
        # compare seulement le type principal (ex: image/png)
        if not any(content_type.startswith(a) for a in allowed):
            return False, "", "mimetype_not_allowed"

    # déterminer nom de fichier
    base_name = safe_filename_from_url(url)
    ext = ext_from_mimetype(content_type) or os.path.splitext(base_name)[1]
    if not ext and not os.path.splitext(base_name)[1]:
        # fallback: use hash
        base_name = f"{base_name}_{hash_url(url)}"
        ext = ""
    if not base_name.endswith(ext):
        base_name = base_name + ext

    ensure_dir(dest_dir)
    filename = unique_filename(dest_dir, base_name)
    local_path = os.path.join(dest_dir, filename)

    # écrire en streaming
    try:
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        return False, "", f"write_error: {e}"

    return True, local_path, filename

def is_file_like_obj(obj: Any, file_keys: List[str]) -> bool:
    if not isinstance(obj, dict):
        return False
    return any(k in obj for k in file_keys)

def find_file_objects(data: Any, file_keys: List[str]) -> List[Tuple[List[Any], Dict]]:
    """
    Parcourt récursivement data et retourne une liste de tuples (path_list, obj_ref)
    path_list : liste de clés/index pour atteindre l'objet depuis la racine
    obj_ref : référence à l'objet dict contenant la clé url/filename/name
    """
    found = []

    def _walk(cur, path):
        if isinstance(cur, dict):
            if is_file_like_obj(cur, file_keys):
                found.append((path.copy(), cur))
            for k, v in cur.items():
                path.append(k)
                _walk(v, path)
                path.pop()
        elif isinstance(cur, list):
            for i, v in enumerate(cur):
                path.append(i)
                _walk(v, path)
                path.pop()
        else:
            return

    _walk(data, [])
    return found

def set_in_data(root: Any, path: List[Any], key: str, value: Any):
    cur = root
    for p in path:
        cur = cur[p]
    cur[key] = value

# -----------------------
# Normalization logic (inchangée, mais appelée après téléchargement)
# -----------------------
def normalize_answer(title: str,
                     answer: Any,
                     qtype: str,
                     cfg: Dict[str, Any]) -> Any:
    if answer is None:
        return None

    # Detect file upload objects: list of dicts with 'url' or 'name'
    if isinstance(answer, list) and answer and isinstance(answer[0], dict):
        if any(k in answer[0] for k in (cfg.get("file_detection_keys") or ["url", "name", "filename"])):
            return answer

    if isinstance(answer, list):
        if cfg.get("parsing", {}).get("unwrap_single_item_lists", True) and len(answer) == 1:
            answer = answer[0]
        else:
            return [normalize_answer(title, a, qtype, cfg) for a in answer]

    if cfg.get("parsing", {}).get("convert_numeric_strings", True):
        if isinstance(answer, str):
            conv = try_convert_number(answer)
            answer = conv

    if cfg.get("parsing", {}).get("parse_dates_iso", True):
        if isinstance(answer, str) and ("date" in (qtype or "").lower() or "date" in (title or "").lower()):
            parsed = try_parse_date(answer)
            answer = parsed

    return answer

# -----------------------
# Build question map (inchangé)
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
# Parse single submission (inchangé, mais utilise normalize_answer)
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
# New: Pre-parse step to download referenced files
# -----------------------
def prefetch_and_download_files(raw: Dict[str, Any], cfg: Dict[str, Any]) -> None:
    """
    Parcourt raw (la structure JSON brute) et télécharge les objets fichier détectés.
    Modifie raw en place en ajoutant des champs localPath/localFilename/downloaded.
    """
    downloads_cfg = cfg.get("downloads", {})
    if not downloads_cfg.get("enabled", False):
        return

    dest_dir = downloads_cfg.get("dir", "data/downloads")
    file_keys = downloads_cfg.get("file_detection_keys", cfg.get("file_detection_keys", ["url", "name", "filename"]))
    allowed_mimetypes = downloads_cfg.get("allowed_mimetypes", [])
    max_size = downloads_cfg.get("max_size_bytes", 0)
    timeout = downloads_cfg.get("timeout_seconds", 30)

    dl_cfg = {
        "allowed_mimetypes": allowed_mimetypes,
        "max_size_bytes": max_size,
        "timeout_seconds": timeout
    }

    # find file-like objects
    found = find_file_objects(raw, file_keys)
    for path, obj in found:
        # prefer explicit mimeType in object if present
        url = obj.get("url") or obj.get("fileUrl") or obj.get("filename") or obj.get("name")
        mime = obj.get("mimeType") or obj.get("contentType") or ""
        if not url or not isinstance(url, str):
            # nothing to download
            set_in_data(raw, path, "downloaded", False)
            set_in_data(raw, path, "download_error", "no_url")
            continue

        # If mime present and allowed list exists, check quickly
        if allowed_mimetypes and mime:
            if not any(mime.startswith(a) for a in allowed_mimetypes):
                set_in_data(raw, path, "downloaded", False)
                set_in_data(raw, path, "download_error", "mimetype_not_allowed")
                continue

        success, local_path_or_err, filename_or_msg = download_file(url, dest_dir, dl_cfg)
        if success:
            # store local info
            set_in_data(raw, path, "localPath", local_path_or_err)
            set_in_data(raw, path, "localFilename", filename_or_msg)
            set_in_data(raw, path, "downloaded", True)
        else:
            set_in_data(raw, path, "downloaded", False)
            set_in_data(raw, path, "download_error", filename_or_msg)

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

    # --- NEW: prefetch/download files referenced in the raw JSON ---
    try:
        prefetch_and_download_files(raw, cfg)
    except Exception as e:
        # ne pas interrompre le parsing si le téléchargement échoue
        print(f"Warning: file prefetch failed: {e}")

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
