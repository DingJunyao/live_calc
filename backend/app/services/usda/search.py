# backend/app/services/usda/search.py
"""USDA 内存索引：空格分词 → OR 子串匹配 → 打分排序。"""
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.usda import UsdaFood


@dataclass
class _Entry:
    fdc_id: int
    desc_lower: str   # 原文小写
    zh: str           # 译文（中文不小写化）


class UsdaSearchIndex:
    """万级数据内存遍历，毫秒级。英文小写化预处理。"""

    def __init__(self, entries: list[_Entry]):
        self.entries = entries

    @classmethod
    def build(cls, db: Session) -> "UsdaSearchIndex":
        rows = db.query(UsdaFood.fdc_id, UsdaFood.description, UsdaFood.description_zh).all()
        entries = [
            _Entry(fdc_id=r[0], desc_lower=(r[1] or "").lower(), zh=(r[2] or ""))
            for r in rows
        ]
        return cls(entries)

    @staticmethod
    def _tokenize(query: str) -> list[str]:
        return [t for t in query.lower().split() if t]

    def _score(self, e: _Entry, tokens: list[str]) -> int:
        """打分：精确 > 前缀 > 包含；命中 token 数加权。命中 0 返回 -1（不入选）。"""
        score = 0
        hit = False
        for t in tokens:
            if not t:
                continue
            in_en = t in e.desc_lower
            in_zh = t in e.zh
            if not (in_en or in_zh):
                continue
            hit = True
            score += 1
            if e.desc_lower == t or e.zh == t:
                score += 100
            elif e.desc_lower.startswith(t) or e.zh.startswith(t):
                score += 10
        return score if hit else -1

    def search(self, query: str, limit: int = 50) -> list[dict]:
        tokens = self._tokenize((query or "")[:200])
        if not tokens:
            return []
        scored = []
        for e in self.entries:
            s = self._score(e, tokens)
            if s > 0:
                scored.append((s, e.fdc_id))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [{"fdc_id": fid, "score": s} for s, fid in scored[:limit]]
