"""翻译后端抽象接口与共享资源。"""
from typing import Protocol

# 食材描述翻译专用系统提示（AI 后端复用）
FOOD_TRANSLATION_SYSTEM_PROMPT = """你是食材翻译专家。把英文 USDA 食材描述翻译成简洁中文，用括号补充关键修饰（部位/状态/加工）。
示例：
"Chicken, breast, meat and skin, raw" -> "鸡胸肉（带皮，生）"
"Salmon, raw" -> "三文鱼（生）"
"Almonds, dry roasted, with salt added" -> "杏仁（干烤，加盐）"
要求：只输出译文，不加解释、不加引号；保持与食材语义贴近。"""


class Translator(Protocol):
    """翻译后端统一接口。"""
    name: str

    async def translate_batch(self, texts: list[str]) -> list[str]:
        """批量翻译，返回与 texts 等长的译文列表；单条失败对应位置返回空串。"""
        ...

    async def health_check(self) -> bool:
        """验证配置是否可用（测试连接）。"""
        ...
