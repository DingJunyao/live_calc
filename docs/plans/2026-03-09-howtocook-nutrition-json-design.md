# HowToCook_nutrition_json - 营养数据独立分析仓库

**创建日期:** 2026-03-09
**版本:** 1.0
**项目名称:** HowToCook_nutrition_json

---

## 目录

1. [项目概述](#项目概述)
2. [整体架构](#整体架构)
3. [仓库结构](#仓库结构)
4. [数据处理流程](#数据处理流程)
5. [核心模块设计](#核心模块设计)
6. [Claude Code技能定义](#claude-code技能定义)
7. [Python处理模块](#python处理模块)
8. [输出数据格式](#输出数据格式)
9. [实施计划](#实施计划)
10. [使用说明](#使用说明)

---

## 项目概述

### 项目简介

HowToCook_nutrition_json 是一个独立的数据处理仓库，专注于营养数据的智能匹配和标准化。

**核心职责:**
- 接收来自 HowToCook_json 仓库的食材数据
- 使用 Claude Code AI 进行智能营养匹配
- Python 处理进行数据标准化和格式转换
- 生成可直接导入到主系统的标准化营养数据

**设计原则:**
- 职责分离：只处理营养数据，不涉及菜谱
- 独立运行：完全独立于主工程和菜谱仓库
- 简化使用：固定输出文件名，便于导入
- 可重复运行：支持多次处理，覆盖上次结果

### 与其他仓库的关系

```
┌─────────────────────────────────────────────────────────┐
│  DingJunyao/HowToCook_json                      │
│  职责：菜谱分析和食材提取                       │
│  输出：out/ingredients.json                   │
└─────────────────────────────────────────────────────────┘
                    ↓ 复制
┌─────────────────────────────────────────────────────────┐
│  DingJunyao/HowToCook_nutrition_json (本仓库)   │
│  职责：营养数据匹配和标准化                       │
│  输入：input/ingredients.json                  │
│  输出：output/nutrition_data.json            │
└─────────────────────────────────────────────────────────┘
                    ↓ 复制
┌─────────────────────────────────────────────────────────┐
│  ding/live_calc (主系统)                        │
│  职责：生活成本计算应用                           │
│  导入：nutrition_data.json (固定路径)                │
└─────────────────────────────────────────────────────────┘
```

---

## 整体架构

### 处理流程图

```
┌──────────────────────────────────────────────────────────┐
│            数据处理流程                               │
└──────────────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│  1. 数据读取阶段                                   │
│  - 读取 input/ingredients.json                        │
│  - 验证JSON格式                                      │
│  - 解析食材列表                                      │
└──────────────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│  2. AI营养匹配阶段 (Claude Code Skill)            │
│  - 调用 nutrition_matcher 技能                   │
│  - 批量处理食材 (50个/批次)                        │
│  - 多策略匹配 (AI语义 + 模糊)                     │
│  - 生成匹配结果和置信度                             │
└──────────────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│  3. 数据标准化阶段 (Python)                        │
│  - 解析营养素值和单位                                │
│  - 计算 NRV 百分比                                  │
│  - 标准化数据格式                                    │
│  - 处理子营养素 (如饱和脂肪等)                     │
└──────────────────────────────────────────────────────────┘
                        │
                        ↓
┌──────────────────────────────────────────────────────────┐
│  4. 输出生成阶段                                   │
│  - 生成 output/nutrition_data.json (固定文件名)           │
│  - 包含统计信息和元数据                             │
│  - 格式化输出 (UTF-8, 2空格缩进)                │
└──────────────────────────────────────────────────────────┘
                        │
                        ↓
                    可导入到主系统
```

### 技术栈

**Python:**
- Python 3.8+
- 异步支持 (asyncio)
- JSON 处理
- 类型注解 (typing)

**Claude Code:**
- Claude Sonnet 4.6
- 自定义技能 (nutrition_matcher)
- 批量处理支持

---

## 仓库结构

### 目录结构

```
HowToCook_nutrition_json/
├── README.md                           # 仓库说明文档
├── CLAUDE.md                           # Claude Code 配置
├── .gitignore                          # Git 忽略配置
│
├── input/                              # 输入数据目录
│   └── ingredients.json              # 从菜谱仓库复制的食材数据
│
├── skills/                              # Claude Code 技能定义
│   └── nutrition_matcher.md         # 营养匹配技能定义
│
├── python_processor/                    # Python 处理模块
│   ├── __init__.py
│   ├── config.py                       # 配置管理
│   ├── main.py                        # 主程序入口
│   │
│   ├── utils/                         # 工具模块
│   │   ├── __init__.py
│   │   ├── nrv_calculator.py      # NRV 百分比计算
│   │   ├── unit_parser.py           # 营养素单位解析
│   │   └── data_validator.py       # 数据验证工具
│   │
│   └── processors/                    # 处理器模块
│       ├── __init__.py
│       ├── ingredient_parser.py       # 食材解析器
│       └── nutrition_formatter.py    # 营养数据格式化
│
├── data_sources/                        # 参考数据
│   ├── nrv_standards.json         # 中国营养素参考值 (NRV)
│   └── usda_reference.json         # USDA 营养数据参考
│
├── output/                             # 输出目录
│   └── nutrition_data.json      # 固定文件名的标准化输出
│
└── tests/                              # 测试模块
    ├── test_nrv_calculation.py     # NRV 计算测试
    ├── test_unit_parsing.py        # 单位解析测试
    └── test_output_format.py       # 输出格式测试
```

### .gitignore 配置

```gitignore
# Python 编译文件
__pycache__/
*.py[cod]
*$py.class

# 虚拟环境
venv/
env/
ENV/
.venv/

# IDE 配置
.vscode/
.idea/
*.swp
*.swo

# 输入文件 (从其他仓库复制)
input/

# 输出文件 (可选，如需提交则注释掉)
output/

# 系统文件
.DS_Store
Thumbs.db
```

---

## 数据处理流程

### 详细处理步骤

#### 步骤 1: 数据读取

```python
# 输入格式支持
# 格式1: 直接数组
[
  {"name": "土豆", "aliases": ["马铃薯"], "category": "蔬菜"},
  {"name": "高筋小麦粉", "aliases": ["高筋面粉"], "category": "谷物"}
]

# 格式2: 包含nutrients字段的对象
{
  "ingredients": [
    {"name": "土豆", "aliases": ["马铃薯"], "category": "蔬菜"},
    {"name": "高筋小麦粉", "aliases": ["高筋面粉"], "category": "谷物"}
  ],
  "metadata": {
    "source": "HowToCook_json",
    "generated_at": "2026-03-09T12:00:00Z"
  }
}
```

**处理逻辑:**
1. 检查文件存在性
2. JSON 格式验证
3. 提取食材列表
4. 基本数据验证 (必填字段检查)

#### 步骤 2: AI 营养匹配

**批量处理策略:**
- 每批处理 50 个食材
- 避免单次请求过大
- 失败批次自动跳过并记录

**匹配策略:**
1. AI 语义匹配 (置信度 0.9-1.0)
2. 模糊匹配 (置信度 0.5-0.8)
3. 关键词匹配 (置信度 0.3-0.6)

**错误处理:**
- 技能调用失败时降级到 Python 模糊匹配
- 记录失败原因和未匹配食材

#### 步骤 3: 数据标准化

**标准化内容:**
1. 单位解析和统一 (如 "364 kcal/100g" → 值=364, 单位="kcal")
2. NRV 百分比计算
3. 数据格式标准化
4. 子营养素处理 (如脂肪下的饱和脂肪、反式脂肪)
5. 置信度评分和保留两位小数

**参考基准:**
- 统一基准: 100g
- 标准单位: kcal (能量), g (质量), mg (矿物质/维生素)

#### 步骤 4: 输出生成

**输出结构:**
```json
{
  "nutrient_data": {
    "高筋小麦粉": { ... },
    "土豆": { ... }
  },
  "ai_matches": [
    {
      "chinese_name": "高筋小麦粉",
      "aliases": ["高筋面粉"],
      "usda_id": "20081",
      "confidence": 0.95,
      "match_type": "ai_semantic"
    }
  ],
  "metadata": {
    "version": "1.0",
    "generated_at": "2026-03-09T12:00:00Z",
    "data_source": "HowToCook_json → nutrition_matcher",
    "ai_model": "claude-sonnet-4.6"
  },
  "statistics": {
    "total_ingredients": 150,
    "matched_count": 145,
    "unmatched_count": 5,
    "success_rate": 96.67,
    "average_confidence": 0.87
  }
}
```

---

## 核心模块设计

### 1. 配置管理模块

```python
# python_processor/config.py

import json
from typing import Dict, Any

class Config:
    """配置管理器"""

    # 匹配策略配置
    BATCH_SIZE = 50
    MAX_RETRIES = 3
    TIMEOUT_SECONDS = 120

    # 输出配置
    OUTPUT_FILE = "output/nutrition_data.json"
    INPUT_FILE = "input/ingredients.json"

    # 匹配置置
    MATCH_STRATEGIES = ["ai_semantic", "fuzzy", "keyword"]
    MIN_CONFIDENCE = 0.3
    HIGH_CONFIDENCE_THRESHOLD = 0.8

    @staticmethod
    def load_config(config_path: str = "config.json") -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # 返回默认配置
            return Config.get_default_config()

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "batch_size": Config.BATCH_SIZE,
            "match_strategies": Config.MATCH_STRATEGIES,
            "min_confidence": Config.MIN_CONFIDENCE,
            "high_confidence_threshold": Config.HIGH_CONFIDENCE_THRESHOLD
        }
```

### 2. NRV 计算模块

```python
# python_processor/utils/nrv_calculator.py

from typing import Dict, Optional

class NRVCalculator:
    """中国营养素参考值 (NRV) 计算器"""

    # 中国营养素参考值 (NRV) - 基于GB 28050-2011
    CHINA_NRV: Dict[str, Dict[str, float]] = {
        "energy": {"value": 8400, "unit": "kJ"},  # 2000 kcal
        "protein": {"value": 60, "unit": "g"},
        "fat": {"value": 60, "unit": "g"},
        "carbohydrates": {"value": 300, "unit": "g"},
        "dietary_fiber": {"value": 25, "unit": "g"},
        "sodium": {"value": 2000, "unit": "mg"},
        "calcium": {"value": 800, "unit": "mg"},
        "iron": {"value": 14, "unit": "mg"},
        "zinc": {"value": 11.5, "unit": "mg"},
        "vitamin_a": {"value": 800, "unit": "μg"},
        "vitamin_c": {"value": 100, "unit": "mg"},
        "vitamin_e": {"value": 14, "unit": "mg α-TE"}
    }

    @classmethod
    def calculate(cls, nutrient_name: str, value: float, unit: str) -> float:
        """
        计算 NRV 百分比

        Args:
            nutrient_name: 营养素名称
            value: 营养素值
            unit: 营养素单位

        Returns:
            NRV 百分比 (0-100)
        """
        # 标准化营养素名称
        normalized_name = cls._normalize_nutrient_name(nutrient_name)

        if normalized_name not in cls.CHINA_NRV:
            return 0.0  # 未知营养素，返回0

        nrv_standard = cls.CHINA_NRV[normalized_name]
        standard_value = nrv_standard["value"]
        standard_unit = nrv_standard["unit"]

        try:
            # 简化处理：假设单位一致或可直接换算
            if standard_unit == unit or unit in standard_unit:
                percentage = (value / standard_value) * 100
            else:
                # 能量单位特殊处理 (kJ ↔ kcal)
                if normalized_name == "energy":
                    if unit == "kJ" and standard_unit == "kJ":
                        percentage = (value / standard_value) * 100
                    elif unit == "kcal" and standard_unit == "kJ":
                        # kcal → kJ (1 kcal = 4.184 kJ)
                        value_kj = value * 4.184
                        percentage = (value_kj / standard_value) * 100
                    else:
                        percentage = (value / standard_value) * 100
                else:
                    # 其他单位暂按相同处理
                    percentage = (value / standard_value) * 100

            # 限制在合理范围 (0-150%)
            return max(0.0, min(150.0, round(percentage, 2)))

        except (ZeroDivisionError, ValueError):
            return 0.0

    @staticmethod
    def _normalize_nutrient_name(name: str) -> str:
        """标准化营养素名称"""
        # 营养素别名映射
        aliases = {
            "calories": "energy",
            "kilocalories": "energy",
            "fiber": "dietary_fiber",
            "sugars": "total_sugars",
            "trans_fat": "trans_fatty_acids"
        }
        return aliases.get(name.lower(), name.lower())
```

### 3. 单位解析模块

```python
# python_processor/utils/unit_parser.py

import re
from typing import Tuple

class UnitParser:
    """营养素单位解析器"""

    # 营养素正则表达式模式
    PATTERNS = {
        "energy": r'^(\d+\.?\d*)\s*(kcal|kJ|kilojoules)',
        "mass": r'^(\d+\.?\d*)\s*(g|mg|μg|kg)',
        "general": r'^(\d+\.?\d*)\s*(.+)'
    }

    @classmethod
    def parse_nutrient_string(cls, nutrient_str: str) -> Tuple[float, str]:
        """
        解析营养素字符串，提取值和单位

        Args:
            nutrient_str: 营养素字符串，如 "364 kcal/100g"

        Returns:
            (value, unit) 元组
        """
        if isinstance(nutrient_str, (int, float)):
            return float(nutrient_str), ""

        if isinstance(nutrient_str, dict):
            # 已经是结构化格式
            return nutrient_str.get("value", 0), nutrient_str.get("unit", "")

        if not isinstance(nutrient_str, str):
            return 0.0, ""

        # 尝试匹配各种格式
        nutrient_str = nutrient_str.strip()

        # 格式1: "364 kcal/100g" - 分离单位和值
        if '/' in nutrient_str:
            # 提取主要部分 (如 "364 kcal")
            main_part = nutrient_str.split('/')[0].strip()
            return cls._parse_simple_format(main_part)

        # 格式2: "364 kcal" 或 "10.3 g"
        for pattern_name, pattern in cls.PATTERNS.items():
            match = re.match(pattern, nutrient_str, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                unit = match.group(2)
                return value, unit

        # 格式3: 纯数字
        try:
            value = float(nutrient_str)
            return value, ""
        except ValueError:
            pass

        # 无法解析，返回默认值
        return 0.0, ""

    @staticmethod
    def _parse_simple_format(simple_str: str) -> Tuple[float, str]:
        """解析简单格式 (如 "364 kcal")"""
        parts = simple_str.split()
        if len(parts) >= 2:
            try:
                value = float(parts[0])
                unit = ' '.join(parts[1:])
                return value, unit
            except ValueError:
                pass

        try:
            return float(simple_str), ""
        except ValueError:
            return 0.0, ""
```

### 4. 食材解析器

```python
# python_processor/processors/ingredient_parser.py

from typing import List, Dict, Optional

class IngredientParser:
    """食材数据解析器"""

    @staticmethod
    def validate_ingredient(ingredient: Dict) -> bool:
        """验证食材数据有效性"""
        # 检查必填字段
        if not ingredient.get("name"):
            return False

        # 检查名称长度
        name = ingredient["name"]
        if len(name) < 1 or len(name) > 200:
            return False

        # 检查别名格式
        aliases = ingredient.get("aliases")
        if aliases is not None:
            if not isinstance(aliases, list):
                return False
            if len(aliases) > 10:
                return False

        return True

    @staticmethod
    def normalize_ingredient_name(name: str) -> str:
        """标准化食材名称"""
        # 去除多余空格
        name = name.strip()

        # 统一全半角
        name = name.replace('（', '(').replace('）', ')')

        # 去除常见修饰词 (可选，根据需求)
        # modifiers = ["新鲜", "特级", "精选", "进口", "有机"]
        # for modifier in modifiers:
        #     name = name.replace(modifier, "").strip()

        return name

    @staticmethod
    def extract_key_ingredient_info(ingredient: Dict) -> Dict[str, any]:
        """提取关键食材信息"""
        return {
            "name": IngredientParser.normalize_ingredient_name(ingredient["name"]),
            "aliases": ingredient.get("aliases", []),
            "category": ingredient.get("category", "unclassified"),
            "original_data": ingredient
        }
```

### 5. 营养数据格式化器

```python
# python_processor/processors/nutrition_formatter.py

from typing import Dict, Any
from datetime import datetime

class NutritionFormatter:
    """营养数据格式化器"""

    @staticmethod
    def format_single_nutrient(nutrient_data: Dict) -> Dict[str, Any]:
        """
        格式化单个营养素为标准格式

        Args:
            nutrient_data: 原始营养数据

        Returns:
            标准化营养数据
        """
        return {
            "standard_value": nutrient_data.get("value", 0),
            "standard_unit": nutrient_data.get("unit", ""),
            "reference_amount": 100,
            "reference_unit": "g",
            "measurement_status": "measured",
            "nrv_percent": round(nutrient_data.get("nrv_percent", 0), 2)
        }

    @staticmethod
    def format_ingredient_nutrition(
        ingredient_name: str,
        nutrition_data: Dict
    ) -> Dict[str, Any]:
        """
        格式化单个食材的完整营养数据

        Args:
            ingredient_name: 食材名称
            nutrition_data: 营养数据

        Returns:
            标准化食材营养数据
        """
        return {
            "reference_base": {
                "amount": 100,
                "unit": "g"
            },
            "nutrients": nutrition_data
        }
```

---

## Claude Code技能定义

### nutrition_matcher.md

```markdown
<!-- skills/nutrition_matcher.md -->
# 营养数据智能匹配技能

## 功能描述

基于中文食材名称，使用 AI 语义理解和多策略匹配算法，智能匹配到 USDA 营养数据库。

## 主要特性

- **AI 语义匹配**: 使用 Claude 的语义理解能力，准确理解中英文食材映射
- **多策略匹配**: AI 语义 → 模糊匹配 → 关键词匹配
- **置信度评分**: 为每个匹配结果提供置信度评分
- **批量处理**: 支持批量处理，提高效率
- **错误处理**: 技能调用失败时提供详细错误信息

## 输入数据格式

```json
{
  "ingredients": [
    {
      "name": "高筋小麦粉",
      "aliases": ["高筋面粉", "强筋粉"],
      "category": "谷物"
    },
    {
      "name": "土豆",
      "aliases": ["马铃薯", "洋芋"],
      "category": "蔬菜"
    }
  ],
  "match_strategies": ["ai_semantic", "fuzzy", "keyword"],
  "include_metadata": true
}
```

### 字段说明

- `ingredients`: 食材列表
  - `name`: 食材标准名称 (必填)
  - `aliases`: 别名列表 (可选)
  - `category`: 食材类别 (可选)

- `match_strategies`: 匹配策略列表
  - `ai_semantic`: AI 语义匹配
  - `fuzzy`: 模糊字符串匹配
  - `keyword`: 基于关键词的匹配

- `include_metadata`: 是否包含详细元数据

## 输出数据格式

```json
{
  "matches": [
    {
      "ingredient_name": "高筋小麦粉",
      "aliases": ["高筋面粉", "强筋粉"],
      "matched_nutrition_id": "20081",
      "nutrition_data": {
        "name_en": "Wheat flour, white, all-purpose, enriched",
        "nutrients": {
          "calories": "364 kcal/100g",
          "protein": "10.3 g/100g",
          "total_lipid": "1.0 g/100g",
          "carbohydrate": "75.0 g/100g",
          "sodium": "2 mg/100g"
        }
      },
      "confidence": 0.95,
      "match_method": "ai_semantic",
      "category_match": true
    }
  ],
  "unmatched": [
    {
      "ingredient_name": "某些罕见食材",
      "reason": "no_matching_data",
      "suggested_action": "需要手动添加营养数据"
    }
  ],
  "processing_stats": {
    "total_processed": 150,
    "matched_count": 145,
    "unmatched_count": 5,
    "high_confidence_matches": 120,
    "average_confidence": 0.87
  },
  "model_info": {
    "model": "claude-sonnet-4.6",
    "timestamp": "2026-03-09T12:00:00Z",
    "processing_time_seconds": 3.2
  }
}
```

### 字段说明

- `matches`: 成功匹配的结果
  - `ingredient_name`: 食材名称
  - `matched_nutrition_id`: USDA ID
  - `nutrition_data`: 营养数据 (名称 + 各营养素)
  - `confidence`: 置信度 (0.0-1.0)
  - `match_method`: 匹配方法
  - `category_match`: 类别是否匹配

- `unmatched`: 未匹配的食材
  - `ingredient_name`: 食材名称
  - `reason`: 未匹配原因
  - `suggested_action`: 建议操作

- `processing_stats`: 处理统计
- `model_info`: 模型信息

## 匹配算法

### 1. AI 语义匹配 (优先级: 1.0)

- 使用 Claude 的语义理解能力
- 直接理解中英文映射关系
- 处理同义词、方言词、异体字
- 置信度范围: 0.9-1.0

### 2. 模糊匹配 (优先级: 0.7)

- 基于字符串相似度的匹配
- 使用编辑距离 (Levenshtein Distance)
- 处理拼写错误、字形差异
- 置信度范围: 0.5-0.8

### 3. 关键词匹配 (优先级: 0.4)

- 提取食材名称的核心关键词
- 基于关键词匹配 USDA 数据库
- 处理描述性文本
- 置信度范围: 0.3-0.6

## 特殊处理

### 同义词处理

输入: "土豆" → 匹配: "Potato, raw"
输入: "马铃薯" → 匹配: "Potato, raw"
输入: "洋芋" → 匹配: "Potato, raw"

### 类别辅助

基于食材类别限制匹配范围:
- "谷物" → 仅搜索谷物类营养数据
- "蔬菜" → 仅搜索蔬菜类营养数据
- "肉类" → 仅搜索肉类营养数据

### 置信度计算

```
综合置信度 = (语义匹配分 * 0.6) +
             (模糊匹配分 * 0.3) +
             (关键词匹配分 * 0.1)
```

## 使用说明

### 在 Python 中调用

```python
from claude_code_skills import SkillManager

skill_manager = SkillManager()

match_input = {
    "ingredients": ingredients_list,
    "match_strategies": ["ai_semantic", "fuzzy"],
    "include_metadata": True
}

result = await skill_manager.invoke_skill(
    "nutrition_matcher",
    input_data=match_input
)
```

### 输出结果处理

```python
# 处理匹配结果
for match in result["matches"]:
    if match["confidence"] >= 0.8:
        # 高置信度匹配，直接使用
        process_high_confidence_match(match)
    elif match["confidence"] >= 0.5:
        # 中等置信度，可能需要人工确认
        process_medium_confidence_match(match)
    else:
        # 低置信度，需要更详细检查
        process_low_confidence_match(match)

# 处理未匹配项
for unmatched in result["unmatched"]:
    log_unmatched_ingredient(unmatched)
```

## 性能优化建议

1. **批量处理**: 每批处理 50 个食材，避免单次请求过大
2. **并行匹配**: 对不同食材可并行调用匹配
3. **缓存结果**: 对高频匹配的食材建立缓存
4. **渐进式匹配**: 先用快速方法筛选，再对候选集精匹配

## 错误处理

- 网络超时: 自动重试 3 次
- API 限流: 自动退避后重试
- 格式错误: 返回详细错误信息和建议
- 部分失败: 继续处理其他食材，记录失败项
```

---

## Python处理模块

### 主程序入口

```python
# python_processor/main.py

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from traceback import print_exc

# 本地导入
from config import Config
from utils.nrv_calculator import NRVCalculator
from utils.unit_parser import UnitParser
from processors.ingredient_parser import IngredientParser
from processors.nutrition_formatter import NutritionFormatter

# 假设有一个技能管理器 (实际集成时替换)
class SkillManager:
    """Claude Code 技能管理器 (占位符)"""

    async def invoke_skill(self, skill_name: str, input_data: Dict) -> Any:
        """调用 Claude Code 技能"""
        # TODO: 集成实际的 Claude Code API
        print(f"  调用技能: {skill_name}")
        print(f"  输入: {len(input_data.get('ingredients', []))} 个食材")

        # 模拟返回 (实际使用时删除)
        return self._simulate_skill_response(input_data)

    def _simulate_skill_response(self, input_data: Dict) -> Dict:
        """模拟技能响应 (用于测试)"""
        ingredients = input_data.get('ingredients', [])
        matches = []

        for ingredient in ingredients:
            name = ingredient.get('name', '')
            aliases = ingredient.get('aliases', [])

            # 模拟匹配结果
            matches.append({
                "ingredient_name": name,
                "aliases": aliases,
                "matched_nutrition_id": f"SIMULATED_{hash(name)}",
                "nutrition_data": self._generate_mock_nutrition(name),
                "confidence": 0.85,
                "match_method": "ai_semantic"
            })

        return {
            "matches": matches,
            "unmatched": [],
            "processing_stats": {
                "total_processed": len(ingredients),
                "matched_count": len(matches),
                "unmatched_count": 0,
                "high_confidence_matches": len([m for m in matches if m['confidence'] >= 0.8]),
                "average_confidence": 0.85
            }
        }

    def _generate_mock_nutrition(self, name: str) -> Dict:
        """生成模拟营养数据 (用于测试)"""
        # 根据名称生成合理的模拟数据
        return {
            "name_en": f"Mock {name}",
            "nutrients": {
                "calories": f"{hash(name) % 500 + 100} kcal/100g",
                "protein": f"{hash(name) % 20 + 5:.1f} g/100g",
                "total_lipid": f"{hash(name) % 10:.1f} g/100g",
                "carbohydrate": f"{hash(name) % 50 + 20:.1f} g/100g",
                "sodium": f"{hash(name) % 500 + 100} mg/100g"
            }
        }

class NutritionDataProcessor:
    """营养数据处理器核心"""

    def __init__(self):
        self.config = Config()
        self.skill_manager = SkillManager()
        self.nrv_calc = NRVCalculator()
        self.unit_parser = UnitParser()
        self.ingredient_parser = IngredientParser()
        self.nutrition_formatter = NutritionFormatter()

    async def process(self):
        """完整处理流程"""
        try:
            print("🎯 营养数据处理开始...")
            print("=" * 50)

            # 步骤1: 数据读取
            print("\n📄 [步骤 1/4] 读取食材数据...")
            ingredients = self._load_ingredients()
            print(f"  ✓ 成功读取 {len(ingredients)} 个食材")

            # 步骤2: AI 匹配
            print("\n🧠 [步骤 2/4] Claude Code 营养匹配...")
            matched_data = await self._ai_match_nutrition(ingredients)
            print(f"  ✓ 匹配完成: {matched_data['processing_stats']['matched_count']}/{matched_data['processing_stats']['total_processed']}")
            print(f"  ✓ 平均置信度: {matched_data['processing_stats']['average_confidence']:.2f}")

            # 步骤3: 数据标准化
            print("\n⚙️  [步骤 3/4] 数据标准化处理...")
            standardized_data = self._standardize_data(matched_data)
            print(f"  ✓ 标准化完成")

            # 步骤4: 输出生成
            print("\n📄 [步骤 4/4] 生成输出文件...")
            output_file = self._generate_output(standardized_data)
            print(f"  ✓ 输出文件: {output_file}")

            # 统计信息
            print("\n" + "=" * 50)
            print("📊 处理统计:")
            print(f"  总食材数: {standardized_data['metadata']['statistics']['total_ingredients']}")
            print(f"  成功匹配: {standardized_data['metadata']['statistics']['matched_count']}")
            print(f"  未匹配: {standardized_data['metadata']['statistics']['unmatched_count']}")
            print(f"  成功率: {standardized_data['metadata']['statistics']['success_rate']:.2f}%")

            print("\n✅ 营养数据处理完成！")
            print("=" * 50)

            return output_file

        except FileNotFoundError as e:
            print(f"\n❌ 错误: {e}")
            print("\n📝 请按以下步骤操作:")
            print("  1. cd DingJunyao/HowToCook_json")
            print("  2. 运行菜谱处理脚本生成 out/ingredients.json")
            print("  3. 复制 out/ingredients.json 到本仓库的 input/ 目录")
            print("  4. 重新运行本程序")
            sys.exit(1)

        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            print("\n🔍 错误详情:")
            print_exc()
            sys.exit(1)

    def _load_ingredients(self) -> List[Dict]:
        """读取食材数据"""
        input_file = self.config.INPUT_FILE

        if not os.path.exists(input_file):
            raise FileNotFoundError(
                f"未找到输入文件: {input_file}\n"
                "请从 HowToCook_json 复制 out/ingredients.json 到 input/ 目录"
            )

        print(f"  读取文件: {input_file}")

        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 支持两种格式
        if isinstance(data, dict) and "ingredients" in data:
            ingredients = data["ingredients"]
        elif isinstance(data, list):
            ingredients = data
        else:
            raise ValueError("不支持的 JSON 格式")

        # 验证数据
        validated = []
        for idx, ingredient in enumerate(ingredients, 1):
            if self.ingredient_parser.validate_ingredient(ingredient):
                validated.append(ingredient)
            else:
                print(f"  ⚠️  警告: 第 {idx} 个食材数据无效，已跳过")

        return validated

    async def _ai_match_nutrition(self, ingredients: List[Dict]) -> Dict:
        """Claude Code 营养匹配"""
        batch_size = self.config.BATCH_SIZE
        all_matches = []
        all_unmatched = []

        total_batches = (len(ingredients) - 1) // batch_size + 1

        for i in range(0, len(ingredients), batch_size):
            batch = ingredients[i:i + batch_size]
            batch_num = i // batch_size + 1

            print(f"  处理批次 [{batch_num}/{total_batches}] ({len(batch)} 个食材)...")

            # 准备输入数据
            batch_input = {
                "ingredients": [
                    self.ingredient_parser.extract_key_ingredient_info(ing)
                    for ing in batch
                ],
                "match_strategies": self.config.MATCH_STRATEGIES,
                "include_metadata": True
            }

            try:
                # 调用技能
                batch_result = await self.skill_manager.invoke_skill(
                    "nutrition_matcher",
                    input_data=batch_input
                )

                # 收集结果
                if "matches" in batch_result:
                    all_matches.extend(batch_result["matches"])

                if "unmatched" in batch_result:
                    all_unmatched.extend(batch_result["unmatched"])

                # 批次间隔
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"  ⚠️  批次处理失败: {e}，跳过此批次")
                # 添加为未匹配
                for ing in batch:
                    all_unmatched.append({
                        "ingredient_name": ing.get("name", ""),
                        "reason": f"skill_error: {str(e)}"
                    })

        return {
            "matches": all_matches,
            "unmatched": all_unmatched
        }

    def _standardize_data(self, matched_data: Dict) -> Dict:
        """标准化营养数据"""
        result = {
            "nutrient_data": {},
            "ai_matches": [],
            "metadata": {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "data_source": "HowToCook_json → nutrition_matcher",
                "ai_model": "claude-sonnet-4.6",
                "statistics": {}
            }
        }

        # 处理匹配项
        for match in matched_data.get("matches", []):
            ingredient_name = match.get("ingredient_name", "")

            # 标准化营养数据
            if "nutrition_data" in match:
                standardized_nutrition = self._standardize_single_ingredient(match)
                result["nutrient_data"][ingredient_name] = standardized_nutrition

            # 保存匹配信息
            result["ai_matches"].append({
                "chinese_name": ingredient_name,
                "aliases": match.get("aliases", []),
                "usda_id": match.get("matched_nutrition_id"),
                "confidence": match.get("confidence", 0.5),
                "match_type": match.get("match_method", "unknown")
            })

        # 处理未匹配项
        for unmatched in matched_data.get("unmatched", []):
            ingredient_name = unmatched.get("ingredient_name", "")
            result["nutrient_data"][ingredient_name] = None
            result["ai_matches"].append({
                "chinese_name": ingredient_name,
                "aliases": [],
                "usda_id": None,
                "confidence": 0.0,
                "match_type": "unmatched"
            })

        # 计算统计
        total = len(result["ai_matches"])
        matched = sum(1 for m in result["ai_matches"] if m["confidence"] > 0.5)
        result["metadata"]["statistics"] = {
            "total_ingredients": total,
            "matched_count": matched,
            "unmatched_count": total - matched,
            "success_rate": round(matched / total * 100, 2) if total > 0 else 0,
            "average_confidence": round(
                sum(m["confidence"] for m in result["ai_matches"] if m["confidence"] > 0) / matched,
                2
            ) if matched > 0 else 0
        }

        return result

    def _standardize_single_ingredient(self, match: Dict) -> Dict:
        """标准化单个食材的营养数据"""
        nutrition_data = match["nutrition_data"]
        nutrients = nutrition_data.get("nutrients", {})

        standardized_nutrients = {}

        for nutrient_name, nutrient_values in nutrients.items():
            # 解析单位和值
            parsed = self.unit_parser.parse_nutrient_string(nutrient_values)

            # 计算 NRV 百分比
            nrv_percent = self.nrv_calc.calculate(
                nutrient_name,
                parsed[0],
                parsed[1]
            )

            # 标准化格式
            standardized_nutrients[nutrient_name] = {
                "standard_value": parsed[0],
                "standard_unit": parsed[1],
                "reference_amount": 100,
                "reference_unit": "g",
                "measurement_status": "measured",
                "nrv_percent": nrv_percent
            }

            # 处理子营养素 (如有)
            if "sub_nutrients" in nutrient_values:
                standardized_nutrients[nutrient_name]["sub_nutrients"] = \
                    self._standardize_sub_nutrients(nutrient_values["sub_nutrients"])

        return {
            "reference_base": {
                "amount": 100,
                "unit": "g"
            },
            "nutrients": standardized_nutrients
        }

    def _standardize_sub_nutrients(self, sub_nutrients: Dict) -> Dict:
        """标准化子营养素"""
        result = {}

        for sub_name, sub_values in sub_nutrients.items():
            parsed = self.unit_parser.parse_nutrient_string(sub_values)
            nrv_percent = self.nrv_calc.calculate(sub_name, parsed[0], parsed[1])

            result[sub_name] = {
                "standard_value": parsed[0],
                "standard_unit": parsed[1],
                "reference_amount": 100,
                "reference_unit": "g",
                "measurement_status": "measured",
                "nrv_percent": nrv_percent
            }

        return result

    def _generate_output(self, standardized_data: Dict) -> str:
        """生成输出文件"""
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # 固定文件名
        output_file = os.path.join(output_dir, self.config.OUTPUT_FILE)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(standardized_data, f, ensure_ascii=False, indent=2)

        return output_file


async def main():
    """主程序入口"""
    processor = NutritionDataProcessor()
    await processor.process()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 输出数据格式

### 完整输出结构

```json
{
  "nutrient_data": {
    "高筋小麦粉": {
      "reference_base": {
        "amount": 100,
        "unit": "g"
      },
      "nutrients": {
        "energy": {
          "standard_value": 364.0,
          "standard_unit": "kcal",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 18.20
        },
        "protein": {
          "standard_value": 10.3,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 17.17
        },
        "total_lipid": {
          "standard_value": 1.0,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 1.67,
          "sub_nutrients": {
            "saturated_fatty_acids": {
              "standard_value": 0.2,
              "standard_unit": "g",
              "reference_amount": 100,
              "reference_unit": "g",
              "measurement_status": "measured",
              "nrv_percent": 1.0
            },
            "trans_fatty_acids": {
              "standard_value": 0.0,
              "standard_unit": "g",
              "reference_amount": 100,
              "reference_unit": "g",
              "measurement_status": "zero",
              "nrv_percent": 0.0
            }
          }
        },
        "carbohydrate": {
          "standard_value": 75.0,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 25.0
        },
        "sodium": {
          "standard_value": 2.0,
          "standard_unit": "mg",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 0.1
        }
      }
    },
    "土豆": {
      "reference_base": {
        "amount": 100,
        "unit": "g"
      },
      "nutrients": {
        "energy": {
          "standard_value": 77.0,
          "standard_unit": "kcal",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 3.85
        },
        "protein": {
          "standard_value": 2.0,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 3.33
        },
        "total_lipid": {
          "standard_value": 0.1,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 0.17
        },
        "carbohydrate": {
          "standard_value": 17.0,
          "standard_unit": "g",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 5.67
        },
        "sodium": {
          "standard_value": 5.0,
          "standard_unit": "mg",
          "reference_amount": 100,
          "reference_unit": "g",
          "measurement_status": "measured",
          "nrv_percent": 0.25
        }
      }
    }
  },
  "ai_matches": [
    {
      "chinese_name": "高筋小麦粉",
      "aliases": ["高筋面粉", "强筋粉"],
      "usda_id": "20081",
      "confidence": 0.95,
      "match_type": "ai_semantic"
    },
    {
      "chinese_name": "土豆",
      "aliases": ["马铃薯", "洋芋"],
      "usda_id": "05070",
      "confidence": 0.92,
      "match_type": "ai_semantic"
    },
    {
      "chinese_name": "未匹配食材",
      "aliases": [],
      "usda_id": null,
      "confidence": 0.0,
      "match_type": "unmatched"
    }
  ],
  "metadata": {
    "version": "1.0",
    "generated_at": "2026-03-09T12:00:00Z",
    "data_source": "HowToCook_json → nutrition_matcher",
    "ai_model": "claude-sonnet-4.6",
    "statistics": {
      "total_ingredients": 150,
      "matched_count": 148,
      "unmatched_count": 2,
      "success_rate": 98.67,
      "average_confidence": 0.88
    }
  }
}
```

---

## 实施计划

### 阶段一: 基础设施搭建 (预计2-3天)

**任务清单:**
- [ ] 创建 GitHub 仓库 `HowToCook_nutrition_json`
- [ ] 初始化项目结构
- [ ] 配置 .gitignore
- [ ] 创建 README.md 基础文档
- [ ] 设置 Python 虚拟环境

**验收标准:**
- 仓库结构完整，所有目录创建成功
- README 文档清晰，包含基本使用说明
- 可以运行 `python python_processor/main.py --help`

### 阶段二: 核心模块开发 (预计3-4天)

**任务清单:**
- [ ] 实现配置管理模块 (`config.py`)
- [ ] 实现 NRV 计算器 (`nrv_calculator.py`)
- [ ] 实现单位解析器 (`unit_parser.py`)
- [ ] 实现食材解析器 (`ingredient_parser.py`)
- [ ] 实现营养格式化器 (`nutrition_formatter.py`)
- [ ] 编写单元测试

**验收标准:**
- 所有模块单元测试通过
- 模块职责清晰，无循环依赖
- 代码符合 PEP 8 规范

### 阶段三: Claude Code 技能定义 (预计2-3天)

**任务清单:**
- [ ] 编写 `nutrition_matcher.md` 技能文档
- [ ] 定义输入输出格式
- [ ] 设计匹配算法描述
- [ ] 编写使用示例和错误处理

**验收标准:**
- 技能文档完整，格式规范
- 输入输出格式清晰明确
- 包含详细的使用说明和错误处理

### 阶段四: 主程序集成 (预计2-3天)

**任务清单:**
- [ ] 实现 `main.py` 主程序
- [ ] 集成所有处理模块
- [ ] 实现批量处理逻辑
- [ ] 实现错误处理和降级策略
- [ ] 实现进度显示和统计输出

**验收标准:**
- 可以完整运行数据处理流程
- 批量处理逻辑正确
- 错误处理覆盖所有异常情况
- 统计信息准确显示

### 阶段五: Claude Code 集成 (预计2-3天)

**任务清单:**
- [ ] 实现 `SkillManager` 类
- [ ] 集成真实的 Claude Code API
- [ ] 测试 API 调用和错误处理
- [ ] 优化批量处理性能

**验收标准:**
- Claude Code API 调用成功
- 批量处理性能可接受
- API 错误正确降级处理
- 处理结果符合预期

### 阶段六: 测试和优化 (预计2-3天)

**任务清单:**
- [ ] 编写集成测试
- [ ] 测试完整数据处理流程
- [ ] 测试边界情况和错误处理
- [ ] 性能测试和优化
- [ ] 文档完善

**验收标准:**
- 所有测试用例通过
- 边界情况处理正确
- 处理 100+ 食材在合理时间内完成
- README 文档完整详细

---

## 使用说明

### 准备工作

#### 1. 克隆仓库

```bash
# 克隆本仓库
git clone https://github.com/DingJunyao/HowToCook_nutrition_json.git
cd HowToCook_nutrition_json

# 设置 Python 环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 准备输入数据

```bash
# 进入菜谱仓库
cd ../HowToCook_json

# 运行菜谱处理脚本 (根据具体文档操作)
# 确保生成了 out/ingredients.json

# 复制到营养仓库
cp out/ingredients.json ../HowToCook_nutrition_json/input/
```

### 运行处理

```bash
# 回到营养仓库
cd ../HowToCook_nutrition_json

# 运行主程序
python python_processor/main.py
```

### 查看结果

```bash
# 查看输出文件
cat output/nutrition_data.json

# 或使用 JSON 查看器
python -m json.tool output/nutrition_data.json
```

### 导入到主系统

```bash
# 方式1: 直接复制文件
cp output/nutrition_data.json ../live_calc/backend/data/

# 方式2: 通过 API 导入 (需要主系统实现)
curl -X POST http://localhost:8000/api/v1/nutrition/import \
  -F "file=@output/nutrition_data.json"
```

---

## 注意事项

### 数据质量

- **输入数据**: 确保从最新的菜谱数据生成 ingredients.json
- **匹配准确性**: 检查 AI 匹配结果，必要时手动修正
- **特殊食材**: 罕见食材需要手动补充营养数据
- **单位一致性**: 注意不同来源的单位可能需要换算

### 性能考虑

- **批量大小**: 默认每批 50 个食材，可根据实际情况调整
- **并发控制**: 避免过多并发请求导致限流
- **缓存策略**: 重复运行可考虑缓存已匹配的结果
- **内存管理**: 处理大量食材时注意内存使用

### 安全考虑

- **文件编码**: 统一使用 UTF-8 编码
- **输入验证**: 严格验证输入数据的完整性和正确性
- **错误信息**: 不在日志中暴露敏感信息
- **数据隐私**: 如涉及个人数据，确保合规处理

---

## 故障排查

### 常见问题

#### 1. 找不到输入文件

**症状**: `FileNotFoundError: 未找到输入文件`

**解决**:
```bash
# 检查文件是否存在
ls -la input/

# 重新复制文件
cp ../HowToCook_json/out/ingredients.json input/
```

#### 2. JSON 解析失败

**症状**: `JSONDecodeError: Expecting value`

**解决**:
```bash
# 验证 JSON 格式
python -m json.tool input/ingredients.json

# 检查文件编码
file input/ingredients.json
```

#### 3. Claude Code API 调用失败

**症状**: `APIError: Failed to invoke skill`

**解决**:
```bash
# 检查 API 配置
# 检查网络连接
ping api.claude-code.com

# 查看详细错误日志
# 启用详细日志模式
python python_processor/main.py --verbose
```

#### 4. 内存不足

**症状**: `MemoryError` 或程序崩溃

**解决**:
```bash
# 减小批量大小
# 修改 config.py
BATCH_SIZE = 25

# 增加系统内存或使用更好的机器
```

---

## 附录

### 参考数据源

#### NRV 标准
- 标准名称: 中国营养素参考值 (Nutrient Reference Values)
- 制定机构: 国家卫生健康委员会
- 标准号: GB 28050-2011
- 最新版本: GB 28050-2022

#### USDA 营养数据库
- 数据库名称: USDA National Nutrient Database for Standard Reference
- 最新版本: Legacy SR28 (2024)
- 数据量: 约 8,600 种食物
- 网址: https://fdc.nal.usda.gov/

### 技术术语

- **NRV**: Nutrient Reference Values - 营养素参考值
- **NRV%**: NRV 百分比 - 每份营养素占 NRV 的百分比
- **AI 语义匹配**: 基于自然语言理解的匹配方法
- **模糊匹配**: 基于字符串相似度的匹配方法
- **置信度**: 匹配结果的可信程度 (0.0-1.0)

---

**文档版本:** 1.0
**最后更新:** 2026-03-09
**维护者:** Claude Code Agent
