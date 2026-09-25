from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.cache import invalidate_cached_target
from app.codes import generate_code
from app.deps import CurrentUser, DbSession
from app.models import Link
from app.rate_limiter import rate_limit_per_user
from app.schemas import LinkCreate, LinkOut

router = APIRouter(prefix="/links", tags=["links"])

MAX_CODE_ATTEMPTS = 5


@router.post("", response_model=LinkOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_per_user)])
def create_link(payload: LinkCreate, user: CurrentUser, db: DbSession) -> Link:
    owner_id = user.id
    target_url = str(payload.url)

    for _ in range(MAX_CODE_ATTEMPTS):
        link = Link(code=generate_code(), target_url=target_url, owner_id=owner_id)
        db.add(link)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            continue
        return link

    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Could not generate a unique short code, please retry",
    )


@router.get("", response_model=list[LinkOut])
def list_my_links(
    user: CurrentUser,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Link]:
    stmt = (
        select(Link)
        .where(Link.owner_id == user.id)
        .order_by(Link.created_at.desc(), Link.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(stmt))


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_link(code: str, user: CurrentUser, db: DbSession) -> None:
    link = db.scalar(select(Link).where(Link.code == code, Link.owner_id == user.id))
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link not found")
    db.delete(link)
    db.commit()
    invalidate_cached_target(code)