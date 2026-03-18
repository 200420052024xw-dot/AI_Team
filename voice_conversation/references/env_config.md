# 火山引擎 ASR 凭证配置指南

## 使用场景

本文档适用于以下情况：

- 用户明确提出手动配置环境变量的需求
- 用户需要“一步一步的配置指导”
- 当前会话无法直接注入环境变量，必须手动设置

对于一次性任务，建议直接在当前命令中临时设置环境变量，而不是修改 shell 配置文件。

## 凭证清单

| 环境变量 | 说明 | 是否必需 |
|----------|------|----------|
| `VOLCANO_APP_KEY` | 从火山引擎控制台获取的 App Key | 必需 |
| `VOLCANO_ACCESS_KEY` | 从火山引擎控制台获取的 Access Token | 必需 |
| `VOLCANO_RESOURCE_ID` | 服务资源 ID | 必需 |

### Resource ID 取值

| 模型版本 | Resource ID |
|----------|-------------|
| 豆包录音文件识别模型 1.0 | `volc.bigasr.auc` |
| 豆包录音文件识别模型 2.0 | `volc.seedasr.auc` |

## 安全提示

**群聊场景**：
> 当前为群聊环境，直接发送凭证会造成泄露风险。请切换至私聊模式，或自行完成配置。

**私聊场景**：
> 密钥会经过 AI 处理，存在潜在泄露可能。推荐自行配置；如需协助，请提供 App Key 和 Access Token。

**无法判断时**：一律按群聊处理。

## 配置步骤

### 临时生效（单次使用）

**macOS / Linux**
```bash
export VOLCANO_APP_KEY="你的AppKey"
export VOLCANO_ACCESS_KEY="你的AccessToken"
export VOLCANO_RESOURCE_ID="volc.bigasr.auc"  # 录音文件识别
```

**Windows PowerShell**
```powershell
$env:VOLCANO_APP_KEY = "你的AppKey"
$env:VOLCANO_ACCESS_KEY = "你的AccessToken"
$env:VOLCANO_RESOURCE_ID = "volc.bigasr.auc"
```

### 持久生效（长期使用）

**macOS / Linux（写入 ~/.zshrc）**
```bash
echo 'export VOLCANO_APP_KEY="你的AppKey"' >> ~/.zshrc
echo 'export VOLCANO_ACCESS_KEY="你的AccessToken"' >> ~/.zshrc
echo 'export VOLCANO_RESOURCE_ID="volc.bigasr.auc"' >> ~/.zshrc
source ~/.zshrc
```

## 调用参数说明

录音文件识别请求中的关键参数：

| 参数 | 说明 | 示例 |
|------|------|------|
| `audio.format` | 音频格式 | `wav`, `mp3` |
| `audio.url` | 音频 URL | `http://xxx.com/audio.wav` |
| `audio.language` | 语言 | `zh-CN` |
| `request.model_name` | 模型名称 | `bigmodel` |
| `request.enable_itn` | 阿拉伯数字转中文 | `false` |
| `request.enable_punc` | 标点 | `false` |

## 操作规范

- 一次性任务优先当前命令注入，避免修改 `~/.bashrc`、`~/.zshrc`
- 禁止将凭证写入项目代码或配置文件
- 配置完成后直接执行自检或识别，无需额外说明
