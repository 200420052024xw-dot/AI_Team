from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from config.config import get_settings
from script.vector_store import get_vector_store
from script.data_store import get_skill_store
from anthropic.types import TextBlock

settings = get_settings()


def _extract_text_from_message(message) -> str:
    """从MiniMax API响应中提取文本内容（处理ThinkingBlock+TextBlock格式）"""
    for block in message.content:
        if isinstance(block, TextBlock):
            return block.text
    return ""


class SkillAgent:
    """Skill推荐Agent (简化版)"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.skill_store = get_skill_store(settings.SKILLS_JSON)
        self.anthropic = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            base_url=settings.ANTHROPIC_BASE_URL
        ) if settings.ANTHROPIC_API_KEY else None
    
    async def recommend_skills(
        self,
        requirement: str,
        agent_description: str
    ) -> Dict[str, Any]:
        """
        推荐技能

        Args:
            requirement: 任务的完整需求描述
            agent_description: Agent的描述

        Returns:
            包含 isHave, skill_id, download_prompt, download_cmd, description, false_reason 的字典
        """

        # 1. 使用 description + requirement 作为检索查询
        query = f"{requirement}\n{agent_description}"

        # 2. 向量检索
        vector_results = self.vector_store.search_skills(
            query=query,
            top_k=10,
            filters=None
        )

        # 记录检索结果
        print(f"[Vector Search Results] count={len(vector_results)}")

        # 3. 检查是否有结果
        if not vector_results:
            return {
                "isHave": False,
                "skill_id": None,
                "download_prompt": None,
                "download_cmd": None,
                "description": None,
                "false_reason": "知识库中暂无任何技能数据,请先添加技能"
            }

        # 4. 获取所有候选的完整技能信息
        candidates = []
        for vr in vector_results:
            skill = get_skill_store().get_skill(vr['skill_id'])
            if skill:
                candidates.append({
                    "skill": skill,
                    "similarity": vr['similarity']
                })

        if not candidates:
            return {
                "isHave": False,
                "skill_id": None,
                "download_prompt": None,
                "download_cmd": None,
                "description": None,
                "false_reason": "检索到的技能数据已被删除"
            }

        # 5. 发送给 LLM 让它选择最匹配的一个
        if self.anthropic:
            selected_skill = await self._select_best_skill_with_llm(requirement, agent_description, candidates)

            if selected_skill:
                skill_id_value = selected_skill.get('skill_id') or selected_skill.get('id')
                return {
                    "isHave": True,
                    "skill_id": skill_id_value,
                    "download_prompt": selected_skill.get('download_prompt', ''),
                    "download_cmd": selected_skill.get('download_cmd', ''),
                    "description": selected_skill['description'],
                    "false_reason": None
                }
            else:
                return {
                    "isHave": False,
                    "skill_id": None,
                    "download_prompt": None,
                    "download_cmd": None,
                    "description": None,
                    "false_reason": "LLM判定所有候选技能均不匹配需求"
                }

        # 6. 无 LLM 时，选择相似度最高的
        else:
            best_candidate = max(candidates, key=lambda x: x['similarity'])
            skill_id_value = best_candidate['skill'].get('skill_id') or best_candidate['skill'].get('id')
            return {
                "isHave": True,
                "skill_id": skill_id_value,
                "download_prompt": best_candidate['skill'].get('download_prompt', ''),
                "download_cmd": best_candidate['skill'].get('download_cmd', ''),
                "description": best_candidate['skill']['description'],
                "false_reason": None
            }

    async def _select_best_skill_with_llm(
        self,
        requirement: str,
        agent_description: str,
        candidates: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        使用 LLM 从多个候选中选择最匹配的一个

        Args:
            requirement: 任务需求
            agent_description: Agent描述
            candidates: 候选技能列表 [{"skill": {...}, "similarity": 0.x}, ...]

        Returns:
            被选中的技能字典，或 None 表示没有匹配
        """

        # 构建候选列表文本
        candidates_text = []
        for i, cand in enumerate(candidates):
            skill = cand['skill']
            skill_desc = skill.get('description', 'N/A')
            candidates_text.append(
                f"[{i}] 技能名称: {skill.get('name', 'N/A')}\n"
                f"    技能描述: {skill_desc}\n"
                f"    安装命令: {skill.get('download_cmd', 'N/A')}"
            )

        prompt = f"""你是一个严格的技能推荐专家。请根据Agent的能力描述，从候选列表中选择最匹配的一个。

【任务】
用户任务需求: {requirement}
Agent能力描述: {agent_description}

【候选技能列表】
{chr(10).join(candidates_text)}

【选择标准】（必须严格执行）
1. 技能描述中的核心功能必须与Agent描述的能力高度吻合
2. 重点匹配关键词：如Agent说"识别和提取人名、地名"，则应选择能"识别实体"的技能
3. 排除不相关的技能

【输出格式】
评分分析:
- [0] 技能名称: xxx → 功能匹配度:XX/10, 关键词命中:XX/5, 理由:xxx
- [1] ...

最终选择: [X号技能名称]

注意：必须选择与Agent能力描述最匹配的技能！
"""

        try:
            # 记录模型输入
            print(f"[Model Input]\n{prompt}\n")

            message = self.anthropic.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response = _extract_text_from_message(message).strip()

            # 记录模型输出
            print(f"[Model Output]\n{response}\n")

            # 解析响应，提取最终选择
            import re

            # 尝试匹配 格式1: "最终选择: [X]"
            match = re.search(r'最终选择[:\s]*\[?(\d+)\]?', response)
            if match:
                selected_idx = int(match.group(1))
                if 0 <= selected_idx < len(candidates):
                    return candidates[selected_idx]['skill']

            # 尝试匹配 markdown 格式: **[数字]** 或 **[数字] 名称**
            match_markdown = re.search(r'\*\*\[(\d+)\]', response)
            if match_markdown:
                selected_idx = int(match_markdown.group(1))
                if 0 <= selected_idx < len(candidates):
                    return candidates[selected_idx]['skill']

            # 尝试找最高评分(10/10)对应的编号
            match_best = re.search(r'\[(\d+)\]\s*[^\[]*?功能匹配度[:\s]*10/10', response)
            if match_best:
                selected_idx = int(match_best.group(1))
                if 0 <= selected_idx < len(candidates):
                    return candidates[selected_idx]['skill']

            # 尝试找评分最高(哪怕不是10/10)的对应编号
            best_score = 0
            best_idx = None
            for m in re.finditer(r'\[(\d+)\]\s*[^\[]*?功能匹配度[:\s]*(\d+)/10', response):
                score = int(m.group(2))
                if score > best_score:
                    best_score = score
                    best_idx = int(m.group(1))
            if best_idx is not None and best_idx < len(candidates):
                return candidates[best_idx]['skill']

            # 尝试解析旧格式作为回退
            match_old = re.search(r'选中的编号[:\s]*\[?(\d+)\]?', response)
            if match_old:
                selected_idx = int(match_old.group(1))
                if 0 <= selected_idx < len(candidates):
                    return candidates[selected_idx]['skill']

            # 检查是否返回"无匹配"
            if "无匹配" in response or "不匹配" in response:
                return None

            return None

        except Exception as e:
            print(f"[Model Error] {e}")
            return None

    def add_skill(self, skill: Dict[str, Any]):
        """添加技能到向量库"""

        # 生成embedding文本
        embedding_text = f"""
名称: {skill['name']}
描述: {skill['description']}
下载提示: {skill.get('download_prompt', '')}
"""

        # 构建元数据
        metadata = {
            "name": skill['name'],
            "star": skill.get('star', 0),
            "download_count": skill.get('download_count', 0)
        }

        # 添加到向量库
        self.vector_store.add_skill(
            skill['skill_id'],
            embedding_text,
            metadata
        )


# 全局单例
_skill_agent = None


def get_skill_agent() -> SkillAgent:
    """获取Skill Agent单例"""
    global _skill_agent
    if _skill_agent is None:
        _skill_agent = SkillAgent()
    return _skill_agent
