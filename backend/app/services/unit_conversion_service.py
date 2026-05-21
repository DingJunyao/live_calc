"""
单位换算服务
核心改动：
1. 全程使用 Decimal 运算
2. 同类型换算优先用 si_factor
3. 支持 entity override 查询（商品>原料>全局优先级链）
4. 支持密度查询（entity_densities 优先级链，默认水=1000 kg/m³）
5. 不再依赖 base_unit_id 和旧的 UnitConversion 直接查表
"""
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.unit import Unit
from app.models.entity_unit_override import EntityUnitOverride
from app.models.entity_density import EntityDensity
from app.models.region_unit_setting import RegionUnitSetting, UserUnitPreference


# 水的默认密度（kg/m³）
WATER_DENSITY = Decimal("1000")


class UnitConversionService:
    """单位换算服务，提供基于 SI 因子、实体覆盖和密度的换算能力"""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------ #
    #  基础查询
    # ------------------------------------------------------------------ #

    def get_unit_by_abbr(self, abbreviation: str) -> Optional[Unit]:
        """根据缩写获取单位"""
        return self.db.query(Unit).filter(Unit.abbreviation == abbreviation).first()

    # 保留旧方法名的别名，兼容现有调用
    def get_unit_by_abbreviation(self, abbreviation: str) -> Optional[Unit]:
        """根据缩写获取单位（兼容旧接口）"""
        return self.get_unit_by_abbr(abbreviation)

    # ------------------------------------------------------------------ #
    #  同类型 SI 换算
    # ------------------------------------------------------------------ #

    def convert_si(
        self, value: Decimal, from_unit: Unit, to_unit: Unit
    ) -> Optional[Decimal]:
        """
        同类型换算：基于 si_factor
        公式：result = value * from.si_factor / to.si_factor
        仅当两个单位属于同一 unit_type 且均有 si_factor 时可用
        """
        if from_unit.unit_type != to_unit.unit_type:
            return None
        if from_unit.si_factor is None or to_unit.si_factor is None:
            return None
        if to_unit.si_factor == 0:
            return None
        return (value * from_unit.si_factor) / to_unit.si_factor

    # ------------------------------------------------------------------ #
    #  密度查询（优先级链）
    # ------------------------------------------------------------------ #

    def get_density(self, entity_type: str, entity_id: int) -> Decimal:
        """
        获取密度（kg/m³），遵循优先级链：
        1. 直接查 entity_densities 表中 entity_type+entity_id
        2. 如果是 product 且无结果，查关联 ingredient 的密度
        3. 默认返回水的密度 1000 kg/m³
        """
        # 1. 直接查找实体的密度
        density_record = (
            self.db.query(EntityDensity)
            .filter(
                EntityDensity.entity_type == entity_type,
                EntityDensity.entity_id == entity_id,
            )
            .order_by(EntityDensity.confidence.desc())
            .first()
        )
        if density_record is not None:
            return density_record.density

        # 2. 如果是 product，查找关联 ingredient 的密度
        if entity_type == "product":
            from app.models.product_entity import Product
            from app.models.product_ingredient_link import ProductIngredientLink

            product = self.db.query(Product).filter(Product.id == entity_id).first()
            if product is not None and product.ingredient_id is not None:
                # 通过 ingredient_id 查密度
                density_record = (
                    self.db.query(EntityDensity)
                    .filter(
                        EntityDensity.entity_type == "ingredient",
                        EntityDensity.entity_id == product.ingredient_id,
                    )
                    .order_by(EntityDensity.confidence.desc())
                    .first()
                )
                if density_record is not None:
                    return density_record.density

            # 也可以通过 product_ingredient_links 查找
            link = (
                self.db.query(ProductIngredientLink)
                .filter(ProductIngredientLink.product_id == entity_id)
                .first()
            )
            if link is not None:
                density_record = (
                    self.db.query(EntityDensity)
                    .filter(
                        EntityDensity.entity_type == "ingredient",
                        EntityDensity.entity_id == link.ingredient_id,
                    )
                    .order_by(EntityDensity.confidence.desc())
                    .first()
                )
                if density_record is not None:
                    return density_record.density

        # 3. 默认返回水的密度
        return WATER_DENSITY

    # ------------------------------------------------------------------ #
    #  体积 <-> 质量 换算
    # ------------------------------------------------------------------ #

    def convert_volume_to_mass(
        self,
        value: Decimal,
        from_unit: Unit,
        entity_type: str,
        entity_id: int,
    ) -> Optional[Tuple[Decimal, Unit]]:
        """
        体积 -> 质量（通过密度）
        步骤：
        1. 将体积转为 SI 基本单位 m³
        2. 乘以密度得到 kg
        3. 将 kg 转为目标质量单位
        返回 (结果值, 质量单位对象)
        """
        if from_unit.unit_type != "volume":
            return None
        if from_unit.si_factor is None:
            return None

        density = self.get_density(entity_type, entity_id)

        # SI 体积单位是 m³，si_factor 将当前单位换算为 m³
        volume_m3 = value * from_unit.si_factor

        # 质量 = 体积(m³) * 密度(kg/m³)
        mass_kg = volume_m3 * density

        # 查找 SI 基本质量单位（kg）并将结果转换为 kg
        kg_unit = (
            self.db.query(Unit)
            .filter(Unit.unit_type == "mass", Unit.is_si_base == True)
            .first()
        )
        if kg_unit is None:
            # 如果没有标记 is_si_base 的单位，用 si_factor=1 的质量单位
            kg_unit = (
                self.db.query(Unit)
                .filter(Unit.unit_type == "mass", Unit.si_factor == 1)
                .first()
            )

        if kg_unit is not None and kg_unit.si_factor is not None and kg_unit.si_factor != 0:
            mass_in_unit = mass_kg / kg_unit.si_factor
            return (mass_in_unit, kg_unit)

        return (mass_kg, kg_unit) if kg_unit else None

    def convert_mass_to_volume(
        self,
        value: Decimal,
        from_unit: Unit,
        entity_type: str,
        entity_id: int,
    ) -> Optional[Tuple[Decimal, Unit]]:
        """
        质量 -> 体积（通过密度反向计算）
        步骤：
        1. 将质量转为 SI 基本单位 kg
        2. 除以密度得到 m³
        3. 将 m³ 转为常见体积单位（L 或 mL）
        返回 (结果值, 体积单位对象)
        """
        if from_unit.unit_type != "mass":
            return None
        if from_unit.si_factor is None:
            return None

        density = self.get_density(entity_type, entity_id)
        if density == 0:
            return None

        # SI 质量单位是 kg，si_factor 将当前单位换算为 kg
        mass_kg = value * from_unit.si_factor

        # 体积 = 质量(kg) / 密度(kg/m³) => m³
        volume_m3 = mass_kg / density

        # 查找一个合适的体积单位来表示结果（优先 L）
        target_unit = (
            self.db.query(Unit)
            .filter(Unit.abbreviation == "L")
            .first()
        )
        if target_unit is None:
            target_unit = (
                self.db.query(Unit)
                .filter(Unit.unit_type == "volume", Unit.is_si_base == True)
                .first()
            )
        if target_unit is None:
            target_unit = (
                self.db.query(Unit)
                .filter(Unit.unit_type == "volume")
                .order_by(Unit.display_order)
                .first()
            )

        if target_unit is None:
            return None

        if target_unit.si_factor is not None and target_unit.si_factor != 0:
            volume_in_unit = volume_m3 / target_unit.si_factor
        else:
            volume_in_unit = volume_m3

        return (volume_in_unit, target_unit)

    # ------------------------------------------------------------------ #
    #  实体覆盖查询
    # ------------------------------------------------------------------ #

    def get_entity_override(
        self,
        entity_type: str,
        entity_id: int,
        unit_name: str,
    ) -> Optional[EntityUnitOverride]:
        """
        查询实体单位覆盖，遵循优先级链：商品>原料>全局
        - 对于 product：先查 product 自身的覆盖，再查关联 ingredient 的覆盖
        - 对于 ingredient：直接查 ingredient 的覆盖
        """
        # 1. 直接查找实体的覆盖
        override = (
            self.db.query(EntityUnitOverride)
            .filter(
                EntityUnitOverride.entity_type == entity_type,
                EntityUnitOverride.entity_id == entity_id,
                EntityUnitOverride.unit_name == unit_name,
            )
            .first()
        )
        if override is not None:
            return override

        # 2. 如果是 product，查找关联 ingredient 的覆盖
        if entity_type == "product":
            from app.models.product_entity import Product
            from app.models.product_ingredient_link import ProductIngredientLink

            product = self.db.query(Product).filter(Product.id == entity_id).first()
            if product is not None and product.ingredient_id is not None:
                override = (
                    self.db.query(EntityUnitOverride)
                    .filter(
                        EntityUnitOverride.entity_type == "ingredient",
                        EntityUnitOverride.entity_id == product.ingredient_id,
                        EntityUnitOverride.unit_name == unit_name,
                    )
                    .first()
                )
                if override is not None:
                    return override

            link = (
                self.db.query(ProductIngredientLink)
                .filter(ProductIngredientLink.product_id == entity_id)
                .first()
            )
            if link is not None:
                override = (
                    self.db.query(EntityUnitOverride)
                    .filter(
                        EntityUnitOverride.entity_type == "ingredient",
                        EntityUnitOverride.entity_id == link.ingredient_id,
                        EntityUnitOverride.unit_name == unit_name,
                    )
                    .first()
                )
                if override is not None:
                    return override

        return None

    # ------------------------------------------------------------------ #
    #  统一换算入口
    # ------------------------------------------------------------------ #

    def convert(
        self,
        value: Decimal,
        from_unit_abbr: str,
        to_unit_abbr: str,
        entity_type: str = None,
        entity_id: int = None,
    ) -> Optional[Tuple[Decimal, str]]:
        """
        统一换算入口
        返回 (结果值, 换算方式)

        逻辑：
        1. 相同单位 -> 直接返回
        2. 实体覆盖单位 -> entity_override（自定义包装单位换算到质量）
        3. 同类型 -> si_factor 计算
        4. 体积 -> 质量 -> 通过密度
        5. 质量 -> 体积 -> 通过密度反向
        6. 不支持 -> 返回 None
        """
        from_unit = self.get_unit_by_abbr(from_unit_abbr)
        to_unit = self.get_unit_by_abbr(to_unit_abbr)

        # 确保 value 为 Decimal
        if not isinstance(value, Decimal):
            value = Decimal(str(value))

        # 1. 相同单位（两者都在全局单位表中）
        if from_unit and to_unit and from_unit.id == to_unit.id:
            return (value, "si_factor")

        # 2. 实体覆盖单位换算
        #    处理自定义包装单位（如"盒(12个)"）到全局单位（如"g"）的换算
        if entity_type and entity_id:
            override = self.get_entity_override(
                entity_type, entity_id, from_unit_abbr
            )
            if override is not None and override.weight_per_unit is not None:
                if override.weight_unit_id:
                    weight_unit = (
                        self.db.query(Unit)
                        .filter(Unit.id == override.weight_unit_id)
                        .first()
                    )
                else:
                    # weight_unit_id 未设置时默认为 g
                    weight_unit = self.get_unit_by_abbr("g")
                # value 个自定义单位 -> value × conversion_factor 个基础单位
                # -> value × conversion_factor × weight_per_unit g
                base_count = value * (override.conversion_factor or Decimal("1"))
                total_weight = base_count * override.weight_per_unit
                if to_unit and weight_unit:
                    if weight_unit.id == to_unit.id:
                        return (total_weight, "entity_override")
                    # weight_unit -> to_unit (同类型 si_factor)
                    final = self.convert_si(total_weight, weight_unit, to_unit)
                    if final is not None:
                        return (final, "entity_override")
                elif not to_unit:
                    return (total_weight, "entity_override")

        # from_unit 或 to_unit 不在全局单位表中且无实体覆盖
        if not from_unit or not to_unit:
            return None

        # 2.5 计数→质量：使用默认单个重量回退（1个=100g=0.1kg）
        #    仅在无实体覆盖时生效
        DEFAULT_PIECE_WEIGHT_KG = Decimal("0.1")  # 100g
        if from_unit.unit_type == "count" and to_unit.unit_type == "mass":
            weight_kg = value * DEFAULT_PIECE_WEIGHT_KG
            # kg -> to_unit
            kg_unit = self.get_unit_by_abbr("kg")
            if kg_unit:
                final = self.convert_si(weight_kg, kg_unit, to_unit)
                if final is not None:
                    return (final, "default_piece_weight")
            return None

        # 2.6 质量→计数：反向回退
        if from_unit.unit_type == "mass" and to_unit.unit_type == "count":
            # to_unit 的目标质量值
            kg_unit = self.get_unit_by_abbr("kg")
            if kg_unit:
                value_kg = self.convert_si(value, from_unit, kg_unit)
                if value_kg is not None:
                    count = value_kg / DEFAULT_PIECE_WEIGHT_KG
                    return (count.quantize(Decimal("0.001")), "default_piece_weight")
            return None

        # 3. 同类型 -> si_factor
        if from_unit.unit_type == to_unit.unit_type:
            result = self.convert_si(value, from_unit, to_unit)
            if result is not None:
                return (result, "si_factor")
            return None

        # 需要 entity 信息才能做跨类型换算
        if entity_type is None or entity_id is None:
            return None

        # 4. 体积 -> 质量
        if from_unit.unit_type == "volume" and to_unit.unit_type == "mass":
            mass_result = self.convert_volume_to_mass(
                value, from_unit, entity_type, entity_id
            )
            if mass_result is not None:
                mass_value, mass_unit = mass_result
                if mass_unit.id == to_unit.id:
                    return (mass_value, "density")
                final_result = self.convert_si(mass_value, mass_unit, to_unit)
                if final_result is not None:
                    return (final_result, "density")
            return None

        # 5. 质量 -> 体积
        if from_unit.unit_type == "mass" and to_unit.unit_type == "volume":
            vol_result = self.convert_mass_to_volume(
                value, from_unit, entity_type, entity_id
            )
            if vol_result is not None:
                vol_value, vol_unit = vol_result
                if vol_unit.id == to_unit.id:
                    return (vol_value, "density")
                final_result = self.convert_si(vol_value, vol_unit, to_unit)
                if final_result is not None:
                    return (final_result, "density")
            return None

        # 6. 不支持的组合
        return None

    # ------------------------------------------------------------------ #
    #  实体单位列表
    # ------------------------------------------------------------------ #

    def get_entity_units(
        self, entity_type: str, entity_id: int
    ) -> List[Dict]:
        """
        获取实体的自定义单位列表（含回退逻辑）
        优先级：实体自身的覆盖 > 关联原料的覆盖 > 全局默认
        """
        overrides = (
            self.db.query(EntityUnitOverride)
            .filter(
                EntityUnitOverride.entity_type == entity_type,
                EntityUnitOverride.entity_id == entity_id,
            )
            .all()
        )

        result = []
        for override in overrides:
            entry: Dict = {
                "unit_name": override.unit_name,
                "conversion_factor": override.conversion_factor,
                "weight_per_unit": override.weight_per_unit,
                "weight_unit_id": override.weight_unit_id,
                "is_default": override.is_default,
                "source": entity_type,
            }
            result.append(entry)

        # 如果是 product，追加关联 ingredient 的覆盖（不重复）
        if entity_type == "product":
            from app.models.product_entity import Product
            from app.models.product_ingredient_link import ProductIngredientLink

            existing_names = {o.unit_name for o in overrides}

            product = self.db.query(Product).filter(Product.id == entity_id).first()
            ingredient_id = None
            if product is not None and product.ingredient_id is not None:
                ingredient_id = product.ingredient_id
            else:
                link = (
                    self.db.query(ProductIngredientLink)
                    .filter(ProductIngredientLink.product_id == entity_id)
                    .first()
                )
                if link is not None:
                    ingredient_id = link.ingredient_id

            if ingredient_id is not None:
                ing_overrides = (
                    self.db.query(EntityUnitOverride)
                    .filter(
                        EntityUnitOverride.entity_type == "ingredient",
                        EntityUnitOverride.entity_id == ingredient_id,
                    )
                    .all()
                )
                for override in ing_overrides:
                    if override.unit_name not in existing_names:
                        entry = {
                            "unit_name": override.unit_name,
                            "conversion_factor": override.conversion_factor,
                            "weight_per_unit": override.weight_per_unit,
                            "weight_unit_id": override.weight_unit_id,
                            "is_default": override.is_default,
                            "source": "ingredient",
                        }
                        result.append(entry)
                        existing_names.add(override.unit_name)

        return result

    def get_available_units(
        self,
        entity_type: str = None,
        entity_id: int = None,
    ) -> List[Unit]:
        """
        获取可用单位列表（全局 + 实体专属）
        返回全局单位列表，如果提供了实体信息，则标记哪些是实体专属的
        """
        # 全局常用单位
        units = (
            self.db.query(Unit)
            .order_by(Unit.unit_type, Unit.display_order)
            .all()
        )
        return units

    # ------------------------------------------------------------------ #
    #  保留的区域/用户偏好方法
    # ------------------------------------------------------------------ #

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
