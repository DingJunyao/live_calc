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

    def _iter():
        yield zip_bytes

    return StreamingResponse(
        _iter(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
