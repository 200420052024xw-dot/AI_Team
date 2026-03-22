"""
JSON数据存储管理
替代数据库,使用JSON文件存储数据
"""

import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid


class JSONDataStore:
    """JSON数据存储类"""

    def __init__(self, json_file: str):
        self.json_file = json_file
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """确保JSON文件存在"""
        os.makedirs(os.path.dirname(self.json_file), exist_ok=True)
        if not os.path.exists(self.json_file):
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def load_all(self) -> List[Dict[str, Any]]:
        """加载所有数据"""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return []

    def save_all(self, data: List[Dict[str, Any]]):
        """保存所有数据"""
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def add(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """添加一条数据"""
        data = self.load_all()

        # 如果item中已经有id,使用它;否则生成新的
        if 'id' not in item and 'skill_id' not in item:
            item['id'] = str(uuid.uuid4())

        # 如果item中已经有时间戳,使用它;否则生成新的
        if 'created_at' not in item and 'add_time' not in item:
            item['created_at'] = datetime.utcnow().isoformat()

        if 'updated_at' not in item:
            item['updated_at'] = datetime.utcnow().isoformat()

        data.append(item)
        self.save_all(data)
        return item

    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取数据"""
        data = self.load_all()
        for item in data:
            if item.get('id') == item_id:
                return item
        return None

    def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """获取所有数据,支持过滤"""
        data = self.load_all()

        if not filters:
            return data

        # 简单过滤
        filtered = []
        for item in data:
            match = True
            for key, value in filters.items():
                if key not in item or item[key] != value:
                    match = False
                    break
            if match:
                filtered.append(item)

        return filtered

    def update(self, item_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新数据"""
        data = self.load_all()

        for i, item in enumerate(data):
            if item.get('id') == item_id:
                item.update(updates)
                item['updated_at'] = datetime.utcnow().isoformat()
                data[i] = item
                self.save_all(data)
                return item

        return None

    def delete(self, item_id: str) -> bool:
        """删除数据"""
        data = self.load_all()
        original_len = len(data)

        data = [item for item in data if item.get('id') != item_id]

        if len(data) < original_len:
            self.save_all(data)
            return True

        return False

    def count(self) -> int:
        """获取数据总数"""
        return len(self.load_all())


class SkillStore:
    """Skill数据存储"""

    def __init__(self, json_file: str):
        self.store = JSONDataStore(json_file)

    def add_skill(self, skill_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加技能"""
        return self.store.add(skill_data)

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能"""
        # 优先通过 skill_id 查找
        all_skills = self.store.load_all()
        for skill in all_skills:
            if skill.get('skill_id') == skill_id or skill.get('id') == skill_id:
                return skill
        return None

    def get_all_skills(self, category: Optional[str] = None,
                       difficulty_level: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有技能"""
        filters = {}
        if category:
            filters['category'] = category
        if difficulty_level:
            filters['difficulty_level'] = difficulty_level

        return self.store.get_all(filters)

    def update_skill(self, skill_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新技能"""
        return self.store.update(skill_id, updates)

    def delete_skill(self, skill_id: str) -> bool:
        """删除技能"""
        return self.store.delete(skill_id)

    def get_skill_by_ids(self, skill_ids: List[str]) -> List[Dict[str, Any]]:
        """根据ID列表获取技能"""
        all_skills = self.store.load_all()
        return [skill for skill in all_skills
                if skill.get('skill_id') in skill_ids or skill.get('id') in skill_ids]


# 全局实例
_skill_store = None


def get_skill_store(json_file: str = "./data/skills.json") -> SkillStore:
    """获取Skill存储实例"""
    global _skill_store
    if _skill_store is None:
        _skill_store = SkillStore(json_file)
    return _skill_store
