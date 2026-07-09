import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.collaboration import (
    Collaboration,
    CollaborationRateHistory,
    CollaborationStatus,
    RateProposalStatus,
)
from app.models.company import Company
from app.utils.pagination import paginate

_SORTABLE_COLUMNS = {
    "currency": Collaboration.currency,
    "status": Collaboration.status,
    "created_at": Collaboration.created_at,
}


async def get_by_id(session: AsyncSession, collaboration_id: uuid.UUID) -> Collaboration | None:
    return await session.get(Collaboration, collaboration_id)


async def get_active_between(
    session: AsyncSession, company_a_id: uuid.UUID, company_b_id: uuid.UUID
) -> Collaboration | None:
    result = await session.execute(
        select(Collaboration).where(
            or_(
                (Collaboration.initiator_company_id == company_a_id)
                & (Collaboration.target_company_id == company_b_id),
                (Collaboration.initiator_company_id == company_b_id)
                & (Collaboration.target_company_id == company_a_id),
            ),
            Collaboration.status.in_([CollaborationStatus.PENDING, CollaborationStatus.ACCEPTED]),
        )
    )
    return result.scalar_one_or_none()


async def list_for_company(session: AsyncSession, company_id: uuid.UUID) -> list[Collaboration]:
    result = await session.execute(
        select(Collaboration)
        .where(
            or_(
                Collaboration.initiator_company_id == company_id,
                Collaboration.target_company_id == company_id,
            )
        )
        .order_by(Collaboration.created_at.desc())
    )
    return list(result.scalars().all())


async def list_for_company_page(
    session: AsyncSession,
    company_id: uuid.UUID,
    page: int,
    page_size: int,
    search: str | None = None,
    sort_by: str | None = None,
    sort_dir: str = "desc",
) -> tuple[list[Collaboration], int]:
    stmt = select(Collaboration).where(
        or_(
            Collaboration.initiator_company_id == company_id,
            Collaboration.target_company_id == company_id,
        )
    )
    if search:
        pattern = f"%{search}%"
        initiator = aliased(Company)
        target = aliased(Company)
        stmt = (
            stmt.join(initiator, initiator.id == Collaboration.initiator_company_id)
            .join(target, target.id == Collaboration.target_company_id)
            .where(
                or_(
                    initiator.name.ilike(pattern),
                    target.name.ilike(pattern),
                    Collaboration.currency.ilike(pattern),
                )
            )
        )
    column = _SORTABLE_COLUMNS.get(sort_by, Collaboration.created_at)
    stmt = stmt.order_by(column.asc() if sort_dir == "asc" else column.desc())
    return await paginate(session, stmt, page, page_size)


async def get_rate_by_id(
    session: AsyncSession, rate_id: uuid.UUID
) -> CollaborationRateHistory | None:
    return await session.get(CollaborationRateHistory, rate_id)


async def get_pending_proposal(
    session: AsyncSession, collaboration_id: uuid.UUID
) -> CollaborationRateHistory | None:
    result = await session.execute(
        select(CollaborationRateHistory).where(
            CollaborationRateHistory.collaboration_id == collaboration_id,
            CollaborationRateHistory.status == RateProposalStatus.PROPOSED,
        )
    )
    return result.scalar_one_or_none()


async def get_rate_proposal_by_id(
    session: AsyncSession, collaboration_id: uuid.UUID, proposal_id: uuid.UUID
) -> CollaborationRateHistory | None:
    result = await session.execute(
        select(CollaborationRateHistory).where(
            CollaborationRateHistory.collaboration_id == collaboration_id,
            CollaborationRateHistory.id == proposal_id,
        )
    )
    return result.scalar_one_or_none()


async def list_rate_history(
    session: AsyncSession, collaboration_id: uuid.UUID
) -> list[CollaborationRateHistory]:
    result = await session.execute(
        select(CollaborationRateHistory)
        .where(CollaborationRateHistory.collaboration_id == collaboration_id)
        .order_by(CollaborationRateHistory.created_at)
    )
    return list(result.scalars().all())
