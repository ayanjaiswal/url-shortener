from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.codes import is_valid_code
from app.deps import DbSession
from app.models import Link
from app.rate_limiter import rate_limit_per_ip

router = APIRouter(tags=["redirect"])


@router.get("/{code}", dependencies=[Depends(rate_limit_per_ip)])
def redirect_to_target(code: str, db: DbSession) -> RedirectResponse:
    if not is_valid_code(code):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")

    target_url = db.scalar(select(Link.target_url).where(Link.code == code))
    if target_url is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")

    # 302 = temporary, so browsers ask us again every time (needed for click counting
    # and for deleted links to stop working). A 301 would be cached by browsers forever.
    return RedirectResponse(target_url, status_code=status.HTTP_302_FOUND)