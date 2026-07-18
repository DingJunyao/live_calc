"""数据导出路由。"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services.export import export_data

router = APIRouter()


@router.get("/data")
async def export_user_data(
    scope: str = Query("full", pattern="^(full|mine)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出当前用户数据为 zip 并流式下载。"""
    # 全量导出（含他人数据）仅管理员可用，普通用户仅可导出本人数据。
    if scope == "full" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="仅管理员可导出全量数据")
    zip_bytes, _manifest = export_data(db, current_user, scope)
    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    # 真分块流式：把内存中的 zip 切成 64KB 块逐块 yield。
    # 历史踩坑：①假流式（一次性 yield 整包）漏设 Content-Length、chunked 单巨型帧在代理层中断；
    # ②普通 Response（Starlette 自动写 Content-Length）后端直连完美，但 Vite dev proxy
    #   (http-proxy) 转发 ~100MB 的 Content-Length 响应会吞掉最后 1 字节，Chrome 严格校验
    #   Content-Length ≠ 实际字节即判截断 → net::ERR_FAILED（实测直连 104800320 完整、经 proxy
    #   104800319 少 1）。
    # 真分块走 chunked encoding、每帧 64KB 小，代理逐帧 pipe 避开大单体响应的吞字节路径；
    # 生产 Nginx 同样正确处理。注意必须是「真分块」——单块过大会退化为上述 ①②问题。
    def _iter_chunks(data: bytes, size: int = 65536):
        for i in range(0, len(data), size):
            yield data[i:i + size]

    return StreamingResponse(
        _iter_chunks(zip_bytes),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
