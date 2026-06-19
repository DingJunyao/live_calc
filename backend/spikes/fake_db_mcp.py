"""Spike 用最小受控 MCP server。

暴露 db_read 工具，固定返回假数据（单位/克重），用于验证 claude CLI 的
stream-json 输出、MCP 挂载、--resume 与第三方代理 env。
"""
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fake_db")


@mcp.tool()
def db_read(sql: str) -> str:
    """只读查询（spike 固定返回假数据）。"""
    return "id|unit_name|weight_per_unit\n1|个|100\n2|根|100\n3|个|55"


if __name__ == "__main__":
    mcp.run(transport="stdio")
