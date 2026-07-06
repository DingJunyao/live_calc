# JSON 列 != 比较致 PG UndefinedFunction

## 现象

审计字段外键那关修好后，PG 启动导入继续崩：

```
psycopg2.errors.UndefinedFunction: 错误: 操作符不存在: json <> unknown
LINE 3: ...redients.aliases IS NOT NULL AND ingredients.aliases != '[]'
HINT: 没有匹配指定名称和参数类型的操作符. 您也许需要增加明确的类型转换.
[SQL: ... WHERE ingredients.aliases IS NOT NULL AND ingredients.aliases != %(aliases_1)s]
[parameters: {'aliases_1': '[]'}]
```

## 根因

`Ingredient.aliases = Column(JSON)`（[nutrition.py:28](../backend/app/models/nutrition.py#L28)）。三处「按别名查找 ingredient」的查询用了 SQL 层比较空数组：

```python
candidates = self.db.query(Ingredient).filter(
    Ingredient.aliases.isnot(None),
    Ingredient.aliases != "[]"   # ← PG 崩这
).all()
for c in candidates:
    if c.aliases and name in c.aliases:   # ← Python 层已对空 list 兜底
        return c
```

- **SQLite**：JSON 列底层就是 TEXT，`aliases != '[]'` 走字符串比较，OK。
- **PostgreSQL**：`json` 类型没有接受 `unknown`（字符串字面量）的 `<>` 操作符，必须显式类型转换或用 `jsonb`，故崩 `操作符不存在: json <> unknown`。
- **MySQL**：`JSON` 列的 `!=` 行为又另一套。

JSON 列的 SQL 比较在三库的操作符/函数/类型转换全不统一，是跨库最易踩的坑。

三处命中（grep `aliases != "\[\]"`）：
- [enhanced_recipe_import_service.py:67](../backend/app/services/enhanced_recipe_import_service.py#L67)
- [json_recipe_import_service.py:66](../backend/app/services/json_recipe_import_service.py#L66)
- [howtocook.py:298](../backend/app/services/importer/importers/howtocook.py#L298)

## 修复

关键观察：三处的 `for c in candidates: if c.aliases and name in c.aliases` **Python 层已对空 list 兜底**（`c.aliases` 为 `[]` 时 `False` 跳过）。SQL 里那句 `!= "[]"` 本就是个冗余的预过滤优化——删掉它逻辑完全等价，却避开了 JSON 列跨库 SQL 比较的整片雷区。

这比 `cast(Text)`/`json_array_length`/改 `jsonb` 之类的写法都干净（那些要么引入跨库行为差异、要么动表结构）。

三处统一改为：
```python
candidates = self.db.query(Ingredient).filter(
    Ingredient.aliases.isnot(None)  # 空数组由 Python 层 if c.aliases 过滤（JSON 列 SQL 比较跨库不兼容）
).all()
```

保留 `isnot(None)`（`IS NOT NULL` 三库通用）；删除 `!= "[]"`。

## 验证

- `py_compile` 三文件全过。
- grep `!= "(\[\]|\{\})"` 全 `backend/app` 无匹配——确认三处已清，也无其他 JSON 列空值 SQL 比较（预防性扫描干净）。

## 边界 / 遗留

- `Ingredient.aliases.isnot(None)` 保留：`IS NOT NULL` 是通用 SQL，三库一致。
- **潜在 SQLite 隐患（未触不改）**：[ingredient_matcher.py:359](../backend/app/services/ingredient_matcher.py#L359) `Ingredient.aliases.op('?')(name)` 用了 PG json 的 `?` 操作符（检查 key 存在）。PG 的 json/jsonb 支持 `?`，当前 PG 不崩；但 SQLite 不支持 `?` 操作符，若切回 SQLite 走该路径会崩。本次用户在 PG 检验，未触发，仅记录，待 SQLite 端遇到再处理。
- 其他 JSON 列（tags、cooking_steps、images、quantity_range 等）：grep 确认无 `!=` 空值比较，无需改。

## 影响

- 解锁 PG 启动导入的「按别名查找 ingredient」路径（三处）。
- SQLite/MySQL 无影响：删的是冗余 SQL 预过滤，Python 层 `if c.aliases` 兜底，结果集一致（仅多取 `aliases=[]` 的行，ingredient 别名数据量小可忽略）。
- 运行时：uvicorn `--reload` 重启重跑 lifespan，PG 导入将从「崩在 aliases 比较查询」继续推进。
