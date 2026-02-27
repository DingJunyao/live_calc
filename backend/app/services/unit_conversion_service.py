from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from decimal import Decimal
from typing import Dict, Tuple, Optional, List
from app.models.unit import Unit, UnitConversion
from app.models.ingredient_density import IngredientDensity
from app.models.region_unit_setting import RegionUnitSetting, UserUnitPreference
from app.models.nutrition import Ingredient
import json


class UnitConversionService:
    def __init__(self, db: Session):
        self.db = db

    def get_unit_by_abbreviation(self, abbreviation: str) -> Optional[Unit]:
        """根据缩写获取单位"""
        return self.db.query(Unit).filter(Unit.abbreviation == abbreviation).first()

    def convert(self, value: float, from_unit_abbr: str, to_unit_abbr: str, ingredient_name: str = None) -> Optional[float]:
        """单位转换"""
        from_unit = self.get_unit_by_abbreviation(from_unit_abbr)
        to_unit = self.get_unit_by_abbreviation(to_unit_abbr)

        if not from_unit or not to_unit:
            return None

        # 如果是相同的单位，直接返回原值
        if from_unit.id == to_unit.id:
            return value

        # 尝试直接转换
        direct_conversion = self.db.query(UnitConversion).filter(
            and_(
                UnitConversion.from_unit_id == from_unit.id,
                UnitConversion.to_unit_id == to_unit.id
            )
        ).first()

        if direct_conversion:
            result = value * float(direct_conversion.conversion_factor)
            return round(result, direct_conversion.precision)

        # 如果直接转换不存在，检查是否存在通过基础单位的转换
        if from_unit.base_unit_id and to_unit.base_unit_id and from_unit.base_unit_id == to_unit.base_unit_id:
            # 通过共同的基础单位转换
            from_to_base = self.db.query(UnitConversion).filter(
                and_(
                    UnitConversion.from_unit_id == from_unit.id,
                    UnitConversion.to_unit_id == from_unit.base_unit_id
                )
            ).first() if from_unit.base_unit_id != from_unit.id else None

            base_to_to = self.db.query(UnitConversion).filter(
                and_(
                    UnitConversion.from_unit_id == to_unit.base_unit_id,
                    UnitConversion.to_unit_id == to_unit.id
                )
            ).first() if to_unit.base_unit_id != to_unit.id else None

            base_value = value
            if from_to_base:
                base_value = base_value * float(from_to_base.conversion_factor)

            if base_to_to:
                base_value = base_value * float(base_to_to.conversion_factor)

            return round(base_value, 2)

        # 如果还是无法转换，尝试通过SI单位转换
        if from_unit.si_factor and to_unit.si_factor:
            # 转换为SI单位，然后再转换为目标单位
            si_value = value * float(from_unit.si_factor)
            result = si_value / float(to_unit.si_factor)
            return round(result, 2)

        return None

    def convert_volume_to_weight(self, volume: float, volume_unit: str, ingredient_name: str) -> Optional[Tuple[float, str]]:
        """体积到重量转换"""
        from_unit = self.get_unit_by_abbreviation(volume_unit)
        if not from_unit or from_unit.unit_type != "volume":
            return None

        # 查找食材密度信息
        density_info = self.db.query(IngredientDensity).join(
            IngredientDensity.ingredient
        ).filter(
            and_(
                or_(Ingredient.name == ingredient_name, Ingredient.name.like(f'%{ingredient_name}%')),
                IngredientDensity.from_unit_id == from_unit.id,
                IngredientDensity.to_unit_id.in_(
                    self.db.query(Unit.id).filter(Unit.unit_type == "mass").subquery()
                )
            )
        ).first()

        if not density_info:
            return None

        # 使用密度进行转换
        weight = volume * float(density_info.density_value)
        to_unit = self.db.query(Unit).filter(Unit.id == density_info.to_unit_id).first()

        return weight, to_unit.abbreviation

    def convert_weight_to_volume(self, weight: float, weight_unit: str, ingredient_name: str) -> Optional[Tuple[float, str]]:
        """重量到体积转换"""
        from_unit = self.get_unit_by_abbreviation(weight_unit)
        if not from_unit or from_unit.unit_type != "mass":
            return None

        # 查找食材密度信息（注意这里的from_unit_id和to_unit_id顺序）
        density_info = self.db.query(IngredientDensity).join(
            IngredientDensity.ingredient
        ).filter(
            and_(
                or_(Ingredient.name == ingredient_name, Ingredient.name.like(f'%{ingredient_name}%')),
                IngredientDensity.to_unit_id == from_unit.id,  # 这里to_unit是质量单位
                IngredientDensity.from_unit_id.in_(
                    self.db.query(Unit.id).filter(Unit.unit_type == "volume").subquery()
                )
            )
        ).first()

        if not density_info:
            # 如果没有找到直接的质量转体积数据，查找体积转质量的反向数据
            density_info = self.db.query(IngredientDensity).join(
                IngredientDensity.ingredient
            ).filter(
                and_(
                    or_(Ingredient.name == ingredient_name, Ingredient.name.like(f'%{ingredient_name}%')),
                    IngredientDensity.from_unit_id.in_(
                        self.db.query(Unit.id).filter(Unit.unit_type == "volume").subquery()
                    ),
                    IngredientDensity.to_unit_id == from_unit.id  # 目标质量单位
                )
            ).first()

        if not density_info:
            return None

        # 使用密度进行转换 (体积 = 质量 / 密度)
        volume = weight / float(density_info.density_value)
        from_unit = self.db.query(Unit).filter(Unit.id == density_info.from_unit_id).first()

        return volume, from_unit.abbreviation

    def get_preferred_units_for_region(self, region_code: str) -> Dict[str, str]:
        """获取地区首选单位"""
        region_setting = self.db.query(RegionUnitSetting).filter(
            RegionUnitSetting.region_code == region_code
        ).first()

        if not region_setting:
            return {}

        result = {}
        if region_setting.default_mass_unit:
            mass_unit = self.db.query(Unit).filter(Unit.id == region_setting.default_mass_unit).first()
            if mass_unit:
                result['mass'] = mass_unit.abbreviation

        if region_setting.default_volume_unit:
            volume_unit = self.db.query(Unit).filter(Unit.id == region_setting.default_volume_unit).first()
            if volume_unit:
                result['volume'] = volume_unit.abbreviation

        if region_setting.default_length_unit:
            length_unit = self.db.query(Unit).filter(Unit.id == region_setting.default_length_unit).first()
            if length_unit:
                result['length'] = length_unit.abbreviation

        return result

    def get_preferred_units_for_user(self, user_id: int) -> Dict[str, str]:
        """获取用户的单位偏好"""
        user_pref = self.db.query(UserUnitPreference).filter(
            UserUnitPreference.user_id == user_id
        ).first()

        if not user_pref:
            return {}

        result = {}
        if user_pref.preferred_mass_unit:
            mass_unit = self.db.query(Unit).filter(Unit.id == user_pref.preferred_mass_unit).first()
            if mass_unit:
                result['mass'] = mass_unit.abbreviation

        if user_pref.preferred_volume_unit:
            volume_unit = self.db.query(Unit).filter(Unit.id == user_pref.preferred_volume_unit).first()
            if volume_unit:
                result['volume'] = volume_unit.abbreviation

        if user_pref.preferred_length_unit:
            length_unit = self.db.query(Unit).filter(Unit.id == user_pref.preferred_length_unit).first()
            if length_unit:
                result['length'] = length_unit.abbreviation

        result['temperature'] = user_pref.temperature_unit
        return result