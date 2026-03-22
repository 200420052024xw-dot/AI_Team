from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config.config import get_settings
from script.vector_store import get_vector_store
from API.api_skills import router as skills_router
import os

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting recommendation system...")

    # 创建数据目录
    os.makedirs(settings.DATA_DIR, exist_ok=True)

    # 初始化向量库
    vector_store = get_vector_store()

    # 如果向量库为空，从 JSON 加载数据
    if vector_store.get_skill_count() == 0:
        print("Vector store empty, loading skills from JSON...")
        from script.data_store import get_skill_store
        skill_store = get_skill_store(settings.SKILLS_JSON)
        skills = skill_store.get_all_skills()
        for skill in skills:
            embedding_text = f"Name: {skill['name']}\nDescription: {skill['description']}\nDownload Prompt: {skill.get('download_prompt', '')}"
            metadata = {
                'name': skill['name'],
                'star': skill.get('star', 0),
                'download_count': skill.get('download_count', 0)
            }
            vector_store.add_skill(skill['skill_id'], embedding_text, metadata)
        print(f"Loaded {len(skills)} skills into vector store")

    print(f"Skill vector count: {vector_store.get_skill_count()}")
    print("System ready!")
    print(f"API docs: http://localhost:8000/docs")

    yield
    print("Shutting down...")

# 创建FastAPI应用
app = FastAPI(
    title="Skill Recommendation System",
    version=settings.APP_VERSION,
    description="Skill Recommendation System (Lite版 - 无数据库依赖)",
    lifespan=lifespan
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(skills_router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Skill推荐系统 (Lite版)",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "endpoints": {
            "skill_recommendation": f"{settings.API_V1_PREFIX}/skills/recommend"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    vector_store = get_vector_store()
    return {
        "status": "healthy",
        "skill_count": vector_store.get_skill_count()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
