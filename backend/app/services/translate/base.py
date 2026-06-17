"""翻译后端抽象接口与共享资源。"""
from typing import Protocol

# 食材描述翻译专用系统提示（AI 后端复用）
FOOD_TRANSLATION_SYSTEM_PROMPT = """你是食材翻译专家。把英文 USDA 食材描述翻译成简洁中文，用括号补充关键修饰（部位/状态/加工）。
示例：
"Chicken, breast, meat and skin, raw" -> "鸡胸肉（带皮，生）"
"Salmon, raw" -> "三文鱼（生）"
"Almonds, dry roasted, with salt added" -> "杏仁（干烤，加盐）"
要求：只输出译文，不加解释、不加引号；保持与食材语义贴近。"""

# 营养素名称翻译专用系统提示（USDA 营养素常含缩写/脂肪酸记号，需营养学知识）
NUTRIENT_TRANSLATION_SYSTEM_PROMPT = """你是营养学领域的术语翻译专家。把下列 USDA 营养素英文名/缩写翻译成中文标准营养学术语。

这些名称常见情况：
- 脂肪酸缩写与记号：MUFA = 单不饱和脂肪酸、PUFA = 多不饱和脂肪酸、SFA = 饱和脂肪酸；"12:1" 这类记号表示碳链长度:双键数（如 12:1 即含 12 碳 1 双键的脂肪酸），保留记号照译。
- 维生素/矿物质学名与缩写：如 "Vitamin E (alpha-tocopherol)" → 维生素E（α-生育酚）。
- 难以直译的化学名/学名，结合 USDA FoodData Central 的营养素命名习惯给出最贴切的中文名；必要时可在 USDA（https://fdc.nal.usda.gov）查证。

要求：只输出译文，不加解释、不加引号、不编号；每行对应一条输入，行数与输入完全一致。"""


class Translator(Protocol):
    """翻译后端统一接口。"""
    name: str

    async def translate_batch(self, texts: list[str]) -> list[str]:
        """批量翻译，返回与 texts 等长的译文列表；单条失败对应位置返回空串。"""
        ...

    async def health_check(self) -> bool:
        """验证配置是否可用（测试连接）。"""
        ...
