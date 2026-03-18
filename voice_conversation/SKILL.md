---
name: asr-short-recognition
description: >
  火山引擎短语音识别 Skill，适用于短音频（<=60s）转文字。支持普通话、英语、日语、韩语等语种识别。
---

# 火山引擎短语音识别 Skill

火山引擎 ASR（豆包语音识别），提供高性价比的短语音转文字服务。

## 核心执行流

1. **用户给音频要转文字**：
   - 先跑 `process_audio.py` 检查音频信息
   - 时长 <=60s 的短音频直接调用识别
2. **用户刚提供了新的火山引擎凭证**：
   - 优先直接跑 `self_check.py`
   - 自检结果通过后再进入真实识别

## 必须遵守的规则

- **⚠️禁止用模型自身能力替代 ASR⚠️**：脚本失败时，必须返回错误，不得猜测转写内容。
- **缺 `ffmpeg` / `ffprobe` 先自治安装**：先执行 `python3 <SKILL_DIR>/scripts/ensure_ffmpeg.py --execute`，只有失败后才向用户求助。
- **收到新凭证先自检**：默认跑 `python3 <SKILL_DIR>/scripts/self_check.py`，不要先让用户手工试脚本。
- **默认少打断**：除非用户必须补充凭证、明确要求手工配置，或语种确实不确定，否则不要无意义来回确认。
- **密钥安全优先**：
  - 群聊：禁止让用户直接发凭证
  - 私聊：也要先提醒"密钥会经过 LLM，存在泄漏风险"
- **单次任务优先当前命令注入**：不要为了跑一次识别去写配置文件

## 引擎选择

| 语种 | Language 参数 |
|------|---------------|
| 普通话 | `zh-CN` (默认) |
| 英语 | `en-US` |
| 日语 | `ja-JP` |
| 韩语 | `ko-KR` |

## 最小脚本示例

```bash
# 预检音频信息（支持本地文件或 URL）
python3 <SKILL_DIR>/scripts/process_audio.py "<AUDIO_INPUT>"

# 凭证自检
python3 <SKILL_DIR>/scripts/self_check.py

# 短语音识别（仅支持公网 URL）
python3 <SKILL_DIR>/scripts/recognize_information.py "https://example.com/audio.wav" --language zh-CN
```

**注意**：识别 API 目前仅支持公网可访问的 URL，不支持本地文件路径。请先将音频上传至对象存储（COS）或公网服务器。

## 核心脚本清单

- `scripts/process_audio.py`：音频探测（检查时长、采样率、声道）
- `scripts/ensure_ffmpeg.py`：自治安装 `ffmpeg` / `ffprobe`
- `scripts/self_check.py`：凭证与识别能力自检
- `scripts/recognize_information.py`：短语音识别（<=60s）
