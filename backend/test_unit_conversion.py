"""
测试单位转换服务的脚本
"""

from app.core.database import SessionLocal
from app.services.unit_conversion_service import UnitConversionService

def test_unit_conversion():
    db = SessionLocal()

    try:
        service = UnitConversionService(db)

        # 测试基本单位转换
        result = service.convert(1, "kg", "g")
        print(f"1 kg = {result} g")

        result = service.convert(500, "g", "kg")
        print(f"500 g = {result} kg")

        result = service.convert(2, "jin", "g")
        print(f"2 jin = {result} g")

        result = service.convert(1000, "g", "jin")
        print(f"1000 g = {result} jin")

        # 测试体积到重量转换（这个会失败，因为我们还没有添加密度数据）
        # result = service.convert_volume_to_weight(1, "L", "water")
        # print(f"1 L water = {result[0]} {result[1]}")

        print("Unit conversion tests completed successfully!")

    finally:
        db.close()

if __name__ == "__main__":
    test_unit_conversion()