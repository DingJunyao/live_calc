"""
单位匹配服务
用于导入原料和菜谱时自动匹配或创建单位
"""
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.unit import Unit
from app.core.database import SessionLocal


class UnitMatcher:
    """单位匹配器"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self._unit_cache = None

    @property
    def unit_cache(self) -> dict:
        """单位缓存：abbreviation -> Unit"""
        if self._unit_cache is None:
            units = self.db.query(Unit).all()
            self._unit_cache = {u.abbreviation: u for u in units}
            # 同时建立 name -> Unit 的映射（处理中文单位）
            for u in units:
                if u.name not in self._unit_cache:
                    self._unit_cache[u.name] = u
        return self._unit_cache

    def match_unit(
        self,
        unit_str: Optional[str]
    ) -> Tuple[Optional[Unit], bool]:
        """
        匹配单位字符串

        Args:
            unit_str: 单位字符串（如"g"、"kg"、"克"等）

        Returns:
            (Unit, is_new): 匹配到的单位和是否为新创建
        """
        if not unit_str or unit_str.strip() == "":
            return None, False

        unit_str = unit_str.strip()

        # 1. 精确匹配 abbreviation
        if unit_str in self.unit_cache:
            return self.unit_cache[unit_str], False

        # 2. 精确匹配 name（处理中文单位）
        for unit in self.unit_cache.values():
            if unit.name == unit_str:
                return unit, False

        # 3. 模糊匹配（处理大小写、空格等问题）
        unit_lower = unit_str.lower()
        for abbr, unit in self.unit_cache.items():
            if abbr.lower() == unit_lower:
                return unit, False

        # 4. 没有匹配到，创建新单位
        return self._create_unit(unit_str), True

    def _create_unit(
        self,
        unit_str: str
    ) -> Unit:
        """
        创建新单位

        Args:
            unit_str: 单位字符串

        Returns:
            新创建的 Unit 对象
        """
        # 默认创建为计数单位
        unit = Unit(
            name=unit_str,
            abbreviation=unit_str,
            unit_type="count",
            si_factor=1.0,
            is_si_base=False,
            is_common=False,
            display_order=999  # 放在最后
        )

        self.db.add(unit)
        self.db.commit()
        self.db.refresh(unit)

        # 更新缓存
        self._unit_cache[unit_str] = unit

        return unit

    def match_or_create_unit(
        self,
        unit_str: Optional[str]
    ) -> Unit:
        """
        匹配或创建单位（便捷方法）

        Args:
            unit_str: 单位字符串

        Returns:
            单位对象（可能为新创建）
        """
        unit, _ = self.match_unit(unit_str)
        return unit

    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()


def get_unit_matcher(db: Optional[Session] = None) -> UnitMatcher:
    """
    获取单位匹配器（便捷函数）

    Args:
        db: 数据库会话，如果为 None 则创建新会话

    Returns:
        UnitMatcher 实例
    """
    return UnitMatcher(db)
