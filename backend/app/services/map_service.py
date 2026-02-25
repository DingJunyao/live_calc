from typing import Tuple, Dict
from app.config import settings


async def calculate_route(
    from_coords: Tuple[float, float],
    to_coords: Tuple[float, float],
    travel_mode: str = "driving",
    map_provider: str = "amap"
) -> Dict:
    """计算路线"""
    # TODO: 实现各地图服务的路线规划
    # 这里先返回简单计算

    # 计算直线距离（Haversine 公式）
    distance = _haversine_distance(from_coords, to_coords)

    # 根据出行方式估算时间和成本
    if travel_mode == "driving":
        duration = int(distance / 40 * 60)  # 假设平均速度 40 km/h
        cost = distance * 0.5  # 假设每公里 0.5 元
    elif travel_mode == "walking":
        duration = int(distance / 5 * 60)  # 假设步行速度 5 km/h
        cost = 0
    elif travel_mode == "cycling":
        duration = int(distance / 15 * 60)  # 假设骑行速度 15 km/h
        cost = 0
    else:  # transit
        duration = int(distance / 30 * 60)  # 假设公交平均速度 30 km/h
        cost = distance * 1.0  # 假设每公里 1 元

    return {
        "distance": round(distance, 2),
        "duration": duration,
        "cost": round(cost, 2),
        "currency": "CNY"
    }


def _haversine_distance(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> float:
    """计算两点间距离（公里）"""
    import math

    lat1, lon1 = point1
    lat2, lon2 = point2

    # 将经纬度转换为弧度
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine 公式
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # 地球半径（公里）

    return c * r
