import chromadb
from chromadb.config import Settings as ChromaSettings
import os
from sentence_transformers import SentenceTransformer
from config.config import get_settings
from typing import List, Dict, Any

# 设置 HuggingFace 缓存到 F 盘
os.environ["HF_HOME"] = "F:/hf_cache"
os.environ["TRANSFORMERS_CACHE"] = "F:/hf_cache/transformers"

# 本地模型路径
LOCAL_MODEL_PATH = "F:/hf_cache/model"

settings = get_settings()


class VectorStore:
    """向量数据库管理类"""

    def __init__(self):
        # 创建ChromaDB持久化目录
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)

        # 初始化ChromaDB客户端
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 初始化本地Embedding模型
        print(f"Loading Embedding model: {LOCAL_MODEL_PATH}")
        self.embedding_model = SentenceTransformer(LOCAL_MODEL_PATH)
        print("Embedding model loaded")

        # 获取或创建集合
        self.skill_collection = self._get_or_create_collection(settings.SKILL_COLLECTION_NAME)

    def _get_or_create_collection(self, name: str):
        """获取或创建集合"""
        try:
            collection = self.client.get_collection(name)
            print(f"Collection loaded: {name}")
        except Exception:
            collection = self.client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
            print(f"Collection created: {name}")
        return collection

    def generate_embedding(self, text: str) -> List[float]:
        """生成文本的embedding向量"""
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def add_skill(self, skill_id: str, text: str, metadata: Dict[str, Any]):
        """添加skill到向量库"""
        embedding = self.generate_embedding(text)
        self.skill_collection.add(
            ids=[skill_id],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )

    def search_skills(
        self,
        query: str,
        top_k: int = 10,
        filters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """搜索相似的skills"""
        query_embedding = self.generate_embedding(query)

        results = self.skill_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filters
        )

        # 格式化结果
        formatted_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                formatted_results.append({
                    "skill_id": results['ids'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results else None,
                    "similarity": 1 - results['distances'][0][i] if 'distances' in results else None,
                    "document": results['documents'][0][i] if 'documents' in results else None,
                    "metadata": results['metadatas'][0][i] if 'metadatas' in results else {}
                })

        return formatted_results

    def delete_skill(self, skill_id: str):
        """删除skill"""
        try:
            self.skill_collection.delete(ids=[skill_id])
        except:
            pass

    def get_skill_count(self) -> int:
        """获取skill数量"""
        return self.skill_collection.count()


# 全局向量库实例
vector_store = None


def get_vector_store() -> VectorStore:
    """获取向量库实例"""
    global vector_store
    if vector_store is None:
        vector_store = VectorStore()
    return vector_store
