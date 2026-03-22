from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from script.data_store import get_skill_store
from script.skill_agent import get_skill_agent
from config.config import get_settings
import uuid
from datetime import datetime

router = APIRouter(prefix="/skills", tags=["Skills"])
settings = get_settings()


# ============= Pydantic Models =============

class SkillFilters(BaseModel):
    category: Optional[str] = None
    difficulty_level: Optional[List[str]] = None


class SkillRecommendRequest(BaseModel):
    requirement: str = Field(..., description="任务的完整需求描述")
    description: str = Field(..., description="候选skill的描述(角色、职责、能力)，用于向量检索匹配")


class SkillRecommendation(BaseModel):
    skill_id: str
    name: str
    category: Optional[str]
    description: str
    tags: List[str]
    difficulty_level: Optional[str]
    examples: Optional[str]
    match_score: float
    match_reason: str
    rank: int


class SkillRecommendResponse(BaseModel):
    isHave: bool = Field(..., description="是否检索成功")
    skill_id: Optional[str] = Field(None, description="技能编号")
    download_prompt: Optional[str] = Field(None, description="下载的提示词")
    download_cmd: Optional[str] = Field(None, description="下载的命令行")
    description: Optional[str] = Field(None, description="技能描述")
    false_reason: Optional[str] = Field(None, description="检索失败原因")


class SkillCreate(BaseModel):
    """创建技能请求"""
    name: str = Field(..., description="技能名称")
    description: str = Field(..., description="技能描述")
    download_prompt: str = Field(..., description="下载提示词")
    download_cmd: str = Field(..., description="下载命令")
    star: int = Field(0, ge=0, description="收藏量")
    download_count: int = Field(0, ge=0, description="下载数量")


class SkillCreateResponse(BaseModel):
    """创建技能响应"""
    isAdd: bool = Field(..., description="是否添加成功")
    skill_id: Optional[str] = Field(None, description="技能ID")
    false_reason: Optional[str] = Field(None, description="失败原因")


class SkillResponse(BaseModel):
    skill_id: str
    name: str
    description: str
    download_prompt: str
    download_cmd: str
    star: int
    download_count: int
    add_time: Optional[str]


# ============= API Endpoints =============

@router.post("/recommend", response_model=SkillRecommendResponse)
async def recommend_skills(request: SkillRecommendRequest):
    """
    推荐技能
    根据任务需求(requirement)和skill描述(description)进行向量检索匹配，返回最匹配的单个技能
    """
    try:
        skill_agent = get_skill_agent()

        result = await skill_agent.recommend_skills(
            requirement=request.requirement,
            agent_description=request.description
        )

        return result

    except Exception as e:
        # 异常情况也返回 isHave=False 的结构
        return {
            "isHave": False,
            "skill_id": None,
            "download_prompt": None,
            "download_cmd": None,
            "description": None,
            "false_reason": f"系统错误: {str(e)}"
        }


@router.post("/", response_model=SkillCreateResponse)
async def create_skill(skill_data: SkillCreate):
    """
    创建新技能

    添加新技能到知识库
    """
    try:
        skill_store = get_skill_store(settings.SKILLS_JSON)
        skill_agent = get_skill_agent()

        # 检查名称是否重复
        existing_skills = skill_store.get_all_skills()
        if any(s.get('name') == skill_data.name for s in existing_skills):
            return {
                "isAdd": False,
                "skill_id": None,
                "false_reason": f"技能名称 '{skill_data.name}' 已存在"
            }

        # 生成ID和时间
        skill_id = str(uuid.uuid4())
        add_time = datetime.utcnow().isoformat() + "Z"

        # 构建技能数据
        skill = {
            "skill_id": skill_id,
            "name": skill_data.name,
            "description": skill_data.description,
            "download_prompt": skill_data.download_prompt,
            "download_cmd": skill_data.download_cmd,
            "star": skill_data.star,
            "download_count": skill_data.download_count,
            "add_time": add_time
        }

        # 保存到JSON
        saved_skill = skill_store.add_skill(skill)

        # 添加到向量库
        skill_agent.add_skill(saved_skill)

        return {
            "isAdd": True,
            "skill_id": skill_id
        }

    except Exception as e:
        return {
            "isAdd": False,
            "skill_id": None,
            "false_reason": f"添加失败: {str(e)}"
        }


@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: str):
    """获取技能详情"""
    skill_store = get_skill_store(settings.SKILLS_JSON)
    skill = skill_store.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return skill


@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    category: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    limit: int = 50
):
    """列出所有技能"""
    skill_store = get_skill_store(settings.SKILLS_JSON)
    skills = skill_store.get_all_skills(category, difficulty_level)
    return skills[:limit]


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str):
    """删除技能"""
    skill_store = get_skill_store(settings.SKILLS_JSON)
    skill_agent = get_skill_agent()
    
    if not skill_store.get_skill(skill_id):
        raise HTTPException(status_code=404, detail="技能不存在")
    
    # 从向量库删除
    skill_agent.vector_store.delete_skill(skill_id)
    
    # 从JSON删除
    skill_store.delete_skill(skill_id)
    
    return {"message": "删除成功", "skill_id": skill_id}
