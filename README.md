# 双Agent智能推荐系统 (Lite版)

基于 FastAPI 的双智能体推荐系统，使用 JSON 文件存储数据，ChromaDB 存储向量，开箱即用。

## 项目结构

```
├── main.py                    # FastAPI 应用入口
├── config/
│   ├── config.py              # 配置管理 (pydantic-settings)
│   └── .env                   # 环境变量 (API密钥)
├── script/
│   ├── data_store.py          # JSON 数据存储 (SkillStore, TeamStore)
│   ├── vector_store.py        # ChromaDB 向量库 + 火山引擎 embedding
│   ├── skill_agent.py         # Skill 推荐智能体
│   └── team_agent.py          # Team 推荐智能体
├── API/
│   ├── api_skills.py          # Skills CRUD + /recommend 接口
│   └── api_teams.py           # Teams CRUD + /recommend 接口
├── tools/
│   └── test_api.py            # API 测试脚本
├── requirements.txt
├── CLAUDE.md
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `config/.env`，填入必要的 API 密钥：

```bash
# 火山引擎向量API (必填)
VOLC_API_KEY=your-volc-api-key
VOLC_EMBEDDING_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/embeddings
VOLC_EMBEDDING_MODEL=doubao-embedding-text-240715

# Anthropic API (可选，启用LLM重排序)
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### 3. 启动服务

```bash
python main.py
```

首次启动时，系统会自动创建 `data/` 目录。

### 4. 访问 API 文档

- API 地址：http://localhost:8000
- 交互文档：http://localhost:8000/docs

### 5. 运行测试

```bash
python tools/test_api.py
```

## 核心功能

### Skill 推荐

根据自然语言需求，推荐最匹配的技能。

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/skills/recommend",
    json={
        "requirement": "我需要分析客户评论的情感",
        "filters": {
            "category": "NLP"
        },
        "top_k": 3
    }
)

for skill in response.json()['recommendations']:
    print(f"{skill['name']}: {skill['match_score']}")
```

### Team 推荐

根据使用场景，推荐最优的 AI 团队配置。

```python
response = requests.post(
    "http://localhost:8000/api/v1/teams/recommend",
    json={
        "use_case": "构建智能客服系统",
        "industry": "电商",
        "team_size_preference": "3-5",
        "top_k": 2
    }
)

for team in response.json()['recommendations']:
    print(f"{team['team_name']}: {team['match_score']}")
```

## 工作流程

```
用户请求 → FastAPI路由 → Agent推理 → 向量检索(ChromaDB) → 可选LLM重排序 → 返回结果
```

1. **向量检索** - 通过 ChromaDB 进行余弦相似度搜索
2. **元数据过滤** - 按 category、difficulty_level 等条件过滤
3. **LLM 重排序** - 如配置了 ANTHROPIC_API_KEY，使用 LLM 进行智能重排序

## API 端点

### Skills

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/skills/recommend` | 推荐技能 |
| POST | `/api/v1/skills/` | 创建技能 |
| GET | `/api/v1/skills/` | 列出所有技能 |
| GET | `/api/v1/skills/{id}` | 获取技能详情 |
| DELETE | `/api/v1/skills/{id}` | 删除技能 |

### Teams

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/v1/teams/recommend` | 推荐团队配置 |
| POST | `/api/v1/teams/` | 创建团队配置 |
| GET | `/api/v1/teams/` | 列出所有团队配置 |
| GET | `/api/v1/teams/{id}` | 获取团队配置详情 |
| DELETE | `/api/v1/teams/{id}` | 删除团队配置 |

## 配置说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VOLC_API_KEY` | 火山引擎 API 密钥 | - |
| `VOLC_EMBEDDING_ENDPOINT` | 火山引擎 embedding 端点 | `https://ark.cn-beijing.volces.com/api/v3/embeddings` |
| `VOLC_EMBEDDING_MODEL` | embedding 模型 ID | `doubao-embedding-text-240715` |
| `ANTHROPIC_API_KEY` | Anthropic API 密钥 (可选) | - |
| `CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 | `./data/chromadb` |
| `DEFAULT_TOP_K` | 默认返回数量 | 5 |

## 数据管理

### 通过 API 添加

```python
requests.post("http://localhost:8000/api/v1/skills/", json={
    "name": "语音识别",
    "category": "语音处理",
    "description": "将语音转换为文本",
    "tags": ["ASR", "语音"],
    "difficulty_level": "advanced",
    "examples": "会议转录、语音助手"
})
```

API 会同时保存到 JSON 文件并索引到 ChromaDB。

### 直接编辑 JSON

数据文件位于：
- `data/skills.json` - 技能数据
- `data/teams.json` - 团队配置数据

修改后重启服务即可生效。

## 注意事项

1. **并发限制** - JSON 文件存储不适合高并发场景
2. **数据备份** - 定期备份 `data/` 目录
3. **API 密钥** - 不要将包含密钥的 `.env` 文件提交到代码仓库
