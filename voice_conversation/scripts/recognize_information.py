import json
import os
import sys
import time
import uuid

def get_credentials():
    """从环境变量读取火山引擎凭证：VOLCANO_APP_KEY、VOLCANO_ACCESS_KEY、VOLCANO_RESOURCE_ID，缺失时输出错误并退出  """
    app_key = os.getenv("VOLCANO_APP_KEY")
    access_key = os.getenv("VOLCANO_ACCESS_KEY")
    resource_id = os.getenv("VOLCANO_RESOURCE_ID")

    missing_information = []
    if not app_key:
        missing_information.append("缺失VOLCANO_APP_KEY")
    if not access_key:
        missing_information.append("缺失VOLCANO_ACCESS_KEY")
    if not resource_id:
        missing_information.append("缺失VOLCANO_RESOURCE_ID")

    if missing_information:
        error_msg = {
            "error": "CREDENTIALS_NOT_CONFIGURED",
            "message": "Missing Volcano Engine credentials required for ASR.",
            "missing_credentials": missing_information,
            "hint": "Set VOLCANO_APP_KEY, VOLCANO_ACCESS_KEY, VOLCANO_RESOURCE_ID environment variables",
        }
        print(json.dumps(error_msg, ensure_ascii=False, indent=2))
        sys.exit(1) #缺少信息立即终止程序退出

    return app_key, access_key, resource_id



def parse_args():
    """Parse command-line arguments."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Volcengine ASR File Recognition CLI"
    )
    parser.add_argument("input", nargs="?", help="Audio file path or URL")
    parser.add_argument("--stdin", action="store_true", help="Read JSON from stdin")
    parser.add_argument("--language", default="zh-CN", help="Language code (default: zh-CN)")
    parser.add_argument(
        "--format", dest="audio_format", default="wav",
        help="Audio format (default: wav)"
    )
    parser.add_argument(
        "--resource-id",
        default="volc.bigasr.auc",
        help="Resource ID (default: volc.bigasr.auc)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int, default=2,
        help="Polling interval in seconds (default: 2)"
    )
    parser.add_argument(
        "--max-poll-time",
        type=int, default=120,
        help="Max polling time in seconds (default: 120)"
    )

    args = parser.parse_args()

    # Determine input
    input_data = {}

    if args.stdin:
        raw = sys.stdin.read().strip()
        data = json.loads(raw)
        if "audio_url" in data:
            input_data = {"audio_url": data["audio_url"]}
        elif "audio_file" in data:
            input_data = {"audio_file": data["audio_file"]}
        else:
            print(json.dumps({
                "error": "INVALID_STDIN",
                "message": "stdin JSON must contain one of: audio_url, audio_file",
            }, ensure_ascii=False, indent=2))
            sys.exit(1)
    elif args.input:
        value = args.input
        if value.startswith("http://") or value.startswith("https://"):
            input_data = {"audio_url": value}
        elif os.path.isfile(value):
            input_data = {"audio_file": value}
        else:
            print(json.dumps({
                "error": "INVALID_INPUT",
                "message": f"File not found or invalid URL: {value}",
            }, ensure_ascii=False, indent=2))
            sys.exit(1)
    else:
        print(json.dumps({
            "error": "NO_INPUT",
            "message": "No audio input provided.",
            "usage": "python recognize_information.py /path/to/audio.wav",
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    return input_data, args





def submit_task(app_key, access_key, resource_id, audio_url, audio_format, language):
    """提交识别任务"""
    try:
        import requests
    except ImportError:
        print("[INFO] requests not found. ", file=sys.stderr)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "requests", "-q"],
            stdout=sys.stderr,
            stderr=sys.stderr,
        )
        import requests

    request_id = str(uuid.uuid4())

    url = "https://openspeech.bytedance.com/api/v3/sauc/bigmodel"

    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Key": app_key,
        "X-Api-Access-Key": access_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }

    body = {
        "user": {
            "uid": str(uuid.uuid4())
        },
        "audio": {
            "format": audio_format,
            "url": audio_url,
            "language": language
        },
        "request": {
            "model_name": "bigmodel",
            "enable_itn": False,
            "enable_punc": False,
        }
    }

    response = requests.post(url, headers=headers, json=body, timeout=30)

    if response.status_code != 200:
        return None, {
            "error": "SUBMIT_FAILED",
            "status_code": response.status_code,
            "message": response.text,
        }

    result = response.json()
    return result, None


def query_task(app_key, access_key, resource_id, request_id):
    """Query recognition task result from Volcano Engine."""
    try:
        import requests
    except ImportError:
        import requests

    url = "https://openspeech.bytedance.com/api/v3/sauc/bigmodel"

    headers = {
        "Content-Type": "application/json",
        "X-Api-App-Key": app_key,
        "X-Api-Access-Key": access_key,
        "X-Api-Resource-Id": resource_id,
        "X-Api-Request-Id": request_id,
        "X-Api-Sequence": "-1",
    }

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        return None, {
            "error": "QUERY_FAILED",
            "status_code": response.status_code,
            "message": response.text,
        }

    result = response.json()
    return result, None


def recognize_volcano(audio_input, audio_format, language, resource_id, poll_interval, max_poll_time):
    """Main recognition function using Volcano Engine File Recognition API."""
    import subprocess

    app_key, access_key, resource_id_env = get_credentials()
    if not resource_id:
        resource_id = resource_id_env

    # Get audio URL
    audio_url = None
    if "audio_url" in audio_input:
        audio_url = audio_input["audio_url"]
    elif "audio_file" in audio_input:
        audio_file = audio_input["audio_file"]
        # 本地文件需要转换为公网可访问的 URL
        # 当前仅支持 URL 输入，本地文件请先上传至可访问的服务器或对象存储
        return {
            "error": "LOCAL_FILE_NOT_SUPPORTED",
            "message": "本地文件暂不支持，请使用公网可访问的 URL",
            "hint": "请先将音频上传至公网服务器、COS、或使用公网链接",
        }

    if not audio_url:
        return {"error": "NO_AUDIO_SOURCE", "message": "No audio URL available"}

    # Submit task
    result, error = submit_task(app_key, access_key, resource_id, audio_url, audio_format, language)
    if error:
        return error

    # Get request_id from response
    request_id = result.get("request_id")
    if not request_id:
        # If no request_id, check if it's a direct result (some API versions return immediately)
        code = result.get("code")
        if code == 20000000:
            # Success - extract result
            text = result.get("result", {}).get("text", "")
            duration = result.get("audio_info", {}).get("duration", 0)
            return {
                "result": text,
                "audio_duration": duration / 1000.0 if duration else 0,
            }
        elif code in (20000001, 20000002):
            # Need to poll
            request_id = result.get("request_id")
        else:
            return result

    # Poll for result
    start_time = time.time()
    while time.time() - start_time < max_poll_time:
        result, error = query_task(app_key, access_key, resource_id, request_id)
        if error:
            return error

        code = result.get("code")
        if code == 20000000:
            # Success
            text = result.get("result", {}).get("text", "")
            duration = result.get("audio_info", {}).get("duration", 0)
            return {
                "result": text,
                "audio_duration": duration / 1000.0 if duration else 0,
                "request_id": request_id,
            }
        elif code == 20000001:
            # Processing - wait and retry
            time.sleep(poll_interval)
            continue
        elif code == 20000002:
            # In queue - wait and retry
            time.sleep(poll_interval)
            continue
        else:
            # Error
            return result

    return {"error": "TIMEOUT", "message": f"Polling timeout after {max_poll_time} seconds"}


def main():
    import subprocess

    input_data, args = parse_args()

    try:
        result = recognize_volcano(
            audio_input=input_data,
            audio_format=args.audio_format,
            language=args.language,
            resource_id=args.resource_id,
            poll_interval=args.poll_interval,
            max_poll_time=args.max_poll_time,
        )

        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as err:
        error_result = {
            "error": "ASR_ERROR",
            "message": str(err),
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
