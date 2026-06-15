"""数据导出路由。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.services.export import export_data

router = APIRouter()


@router.get("/data")
async def export_user_data(
    scope: str = Query("full", pattern="^(full|mine)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """导出当前用户数据为 zip 并流式下载。"""
    zip_bytes, _manifest = export_data(db, current_user, scope)
    filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    def _iter():
        yield zip_bytes

    return StreamingResponse(
        _iter(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
