#!/usr/bin/env python3
"""Volcengine ASR credential self-check."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


DEFAULT_POLL_INTERVAL = 2
DEFAULT_MAX_POLL_TIME = 120


def fail(message, exit_code=1):
    print(json.dumps({"error": "SELF_CHECK_FAILED", "message": message}, ensure_ascii=False, indent=2))
    raise SystemExit(exit_code)


def skill_dir():
    return Path(__file__).resolve().parents[1]


def script_path(name):
    path = skill_dir() / "scripts" / name
    if not path.exists():
        fail(f"Missing script: {path}")
    return path


def default_sample_candidates():
    base = skill_dir()
    return [
        base / "assets" / "16k.wav",
        base / "assets" / "self-check" / "16k.wav",
        base / "16k.wav",
    ]


def resolve_sample_path(explicit_path):
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path.resolve()
        fail(f"Self-check sample does not exist: {path}")

    for candidate in default_sample_candidates():
        if candidate.exists():
            return candidate.resolve()

    fail(
        "No self-check sample audio found. Put 16k.wav under the skill assets directory "
        "or pass --sample /absolute/path/to/16k.wav."
    )


def parse_json_documents(stdout):
    documents = []
    decoder = json.JSONDecoder()
    index = 0
    length = len(stdout)

    while index < length:
        while index < length and stdout[index].isspace():
            index += 1
        if index >= length:
            break
        try:
            payload, end = decoder.raw_decode(stdout, index)
        except json.JSONDecodeError:
            return []
        documents.append(payload)
        index = end

    return documents


def run_command(command, allow_nonzero=False):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0 and not allow_nonzero:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Command failed")
    return result


def run_json_command(command):
    result = run_command(command, allow_nonzero=True)
    payloads = parse_json_documents(result.stdout)
    payload = payloads[-1] if payloads else None
    return result, payload


def ensure_ffmpeg():
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        return {"status": "already_available"}

    result, payload = run_json_command([sys.executable, str(script_path("ensure_ffmpeg.py")), "--execute"])
    if result.returncode != 0:
        message = "Failed to prepare ffmpeg/ffprobe."
        if isinstance(payload, dict):
            message = payload.get("message") or payload.get("error") or message
        fail(message)
    return payload or {"status": "installed"}


def prepare_sample_audio(sample_path, output_dir):
    prepared_path = output_dir / "self_check.wav"
    normalize_command = [
        "ffmpeg",
        "-y",
        "-i",
        str(sample_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(prepared_path),
    ]
    run_command(normalize_command)
    return prepared_path


def transcript_preview(text, limit=60):
    if text is None:
        return None
    normalized = " ".join(str(text).split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1] + "…"


def build_check(mode, label, status, audio_path, payload=None, stderr="", returncode=0):
    payload = payload or {}
    error = payload.get("error")
    message = payload.get("message") or payload.get("error_msg") or stderr.strip()
    transcript = payload.get("result")

    emoji = {"passed": "✅", "failed": "❌", "skipped": "⚠️"}.get(status, "⚠️")
    check = {
        "mode": mode,
        "label": label,
        "status": status,
        "emoji": emoji,
        "audio_path": str(audio_path),
        "returncode": returncode,
    }

    if transcript is not None:
        check["transcript_preview"] = transcript_preview(transcript)
    if payload.get("audio_duration") is not None:
        check["audio_duration"] = payload["audio_duration"]
    if error:
        check["error"] = error
    if message:
        check["message"] = message
    return check


def run_asr_check(mode, label, command, audio_path):
    result, payload = run_json_command(command)
    if result.returncode == 0 and isinstance(payload, dict) and payload.get("result") is not None:
        return build_check(mode, label, "passed", audio_path, payload=payload, returncode=0)

    payload = payload or {}
    return build_check(mode, label, "failed", audio_path, payload=payload, stderr=result.stderr, returncode=result.returncode)


def classify_result(checks):
    passed = {check["mode"] for check in checks if check["status"] == "passed"}
    failed = {check["mode"] for check in checks if check["status"] == "failed"}
    skipped = {check["mode"] for check in checks if check["status"] == "skipped"}

    if passed == {"sentence"}:
        return "success"
    if failed == {"sentence"}:
        return "all_failed"
    return "partial"


def build_guidance(classification, checks):
    lines = []

    if classification == "success":
        lines.append("✅ 流式语音识别自检通过，可以继续正常使用。")
        return lines

    if classification == "all_failed":
        lines.append("❌ 语音识别没有通过自检。")
        lines.append("请优先检查你提供的火山引擎凭证是否有效、ASR 服务是否已开通。")
        lines.append("确认环境变量 VOLCANO_APP_KEY、VOLCANO_ACCESS_KEY、VOLCANO_RESOURCE_ID 是否正确配置。")
        return lines

    lines.append("⚠️ 自检未得到完整结果。")
    lines.append("请根据失败模式对应的错误信息继续排查。")
    return lines


def build_report(classification, checks, sample_path):
    header = {
        "success": "✅ 自检通过",
        "all_failed": "❌ 自检失败",
        "partial": "⚠️ 自检部分通过",
    }[classification]

    lines = [
        f"{header}",
        f"样例音频：{sample_path}",
        "",
    ]

    for check in checks:
        line = f"{check['emoji']} {check['label']}"
        if check.get("transcript_preview"):
            line += f"：{check['transcript_preview']}"
        elif check.get("message"):
            line += f"：{check['message']}"
        lines.append(line)

    guidance = build_guidance(classification, checks)
    if guidance:
        lines.append("")
        lines.extend(guidance)

    return "\n".join(lines)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Volcano Engine ASR self-check with a bundled sample.")
    parser.add_argument("--sample", help="Path to the sample WAV used for self-check.")
    parser.add_argument("--language", default="zh-CN", help="Language code (default: zh-CN)")
    parser.add_argument("--resource-id", default="volc.bigasr.auc", help="Resource ID")
    return parser.parse_args()


def check_credentials():
    """Check if Volcano credentials are configured."""
    app_key = os.getenv("VOLCANO_APP_KEY")
    access_key = os.getenv("VOLCANO_ACCESS_KEY")
    resource_id = os.getenv("VOLCANO_RESOURCE_ID")

    missing = []
    if not app_key:
        missing.append("VOLCANO_APP_KEY")
    if not access_key:
        missing.append("VOLCANO_ACCESS_KEY")
    if not resource_id:
        missing.append("VOLCANO_RESOURCE_ID")

    if missing:
        return {
            "status": "failed",
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": f"Missing environment variables: {', '.join(missing)}",
            "hint": "Set VOLCANO_APP_KEY, VOLCANO_ACCESS_KEY, VOLCANO_RESOURCE_ID",
        }
    return {"status": "passed"}


def main():
    args = parse_args()

    # Check credentials first
    cred_check = check_credentials()
    if cred_check["status"] != "passed":
        print(json.dumps({
            "status": "failed",
            "credential_check": cred_check,
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": cred_check["message"],
            "hint": cred_check["hint"],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    sample_path = resolve_sample_path(args.sample)
    ffmpeg_status = ensure_ffmpeg()

    # 火山引擎 API 需要公网 URL，无法在本地自检
    # 返回提示信息，引导用户使用公网 URL 进行测试
    classification = "skipped"
    checks = [
        {
            "mode": "sentence",
            "label": "流式语音识别",
            "status": "skipped",
            "emoji": "⚠️",
            "audio_path": str(sample_path),
            "message": "自检需要公网可访问的 URL，请手动使用公网音频链接测试识别功能",
        },
    ]

    payload = {
        "status": classification,
        "sample_path": str(sample_path),
        "ffmpeg_status": ffmpeg_status,
        "checks": checks,
        "guidance": build_guidance(classification, checks),
        "report_markdown": build_report(classification, checks, sample_path),
        "note": "火山引擎录音文件识别 API 需要公网 URL，请在确认凭证配置正确后，使用公网音频链接进行实际识别测试",
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
