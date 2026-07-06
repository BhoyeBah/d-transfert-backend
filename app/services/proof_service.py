import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, NotFoundError
from app.models.proof import Proof
from app.repositories import proof_repository
from app.services import payment_service, transfer_service

settings = get_settings()

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


def _validate_file(content_type: str | None, size: int) -> str:
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise AppError(
            "Type de fichier non autorisé. Formats acceptés : JPEG, PNG, WEBP, PDF."
        )
    max_size = settings.max_upload_size_mb * 1024 * 1024
    if size > max_size:
        raise AppError(f"Le fichier dépasse la taille maximale autorisée ({settings.max_upload_size_mb} Mo).")
    if size == 0:
        raise AppError("Le fichier est vide.")
    return _ALLOWED_CONTENT_TYPES[content_type]


def _store_file(company_id: uuid.UUID, extension: str, content: bytes) -> str:
    company_dir = Path(settings.upload_dir) / str(company_id)
    company_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{extension}"
    destination = company_dir / stored_name
    destination.write_bytes(content)
    return str(destination)


async def upload_transfer_proof(
    session: AsyncSession,
    company_id: uuid.UUID,
    uploaded_by_id: uuid.UUID,
    transfer_id: uuid.UUID,
    file_name: str,
    content_type: str | None,
    content: bytes,
    note: str | None,
) -> Proof:
    await transfer_service.get_transfer(session, company_id, transfer_id)
    extension = _validate_file(content_type, len(content))
    storage_path = _store_file(company_id, extension, content)
    proof = Proof(
        company_id=company_id,
        transfer_id=transfer_id,
        uploaded_by_id=uploaded_by_id,
        file_name=file_name[:255],
        storage_path=storage_path,
        content_type=content_type,
        file_size=len(content),
        note=note,
    )
    proof = await proof_repository.create(session, proof)
    await session.commit()
    return proof


async def upload_payment_proof(
    session: AsyncSession,
    company_id: uuid.UUID,
    uploaded_by_id: uuid.UUID,
    payment_id: uuid.UUID,
    file_name: str,
    content_type: str | None,
    content: bytes,
    note: str | None,
) -> Proof:
    await payment_service.get_payment(session, company_id, payment_id)
    extension = _validate_file(content_type, len(content))
    storage_path = _store_file(company_id, extension, content)
    proof = Proof(
        company_id=company_id,
        payment_id=payment_id,
        uploaded_by_id=uploaded_by_id,
        file_name=file_name[:255],
        storage_path=storage_path,
        content_type=content_type,
        file_size=len(content),
        note=note,
    )
    proof = await proof_repository.create(session, proof)
    await session.commit()
    return proof


async def list_transfer_proofs(session: AsyncSession, company_id: uuid.UUID, transfer_id: uuid.UUID) -> list[Proof]:
    await transfer_service.get_transfer(session, company_id, transfer_id)
    return await proof_repository.list_by_transfer(session, transfer_id)


async def list_payment_proofs(session: AsyncSession, company_id: uuid.UUID, payment_id: uuid.UUID) -> list[Proof]:
    await payment_service.get_payment(session, company_id, payment_id)
    return await proof_repository.list_by_payment(session, payment_id)


async def get_transfer_proof_file(
    session: AsyncSession, company_id: uuid.UUID, transfer_id: uuid.UUID, proof_id: uuid.UUID
) -> Proof:
    await transfer_service.get_transfer(session, company_id, transfer_id)
    proof = await proof_repository.get_by_id(session, proof_id)
    if proof is None or proof.transfer_id != transfer_id:
        raise NotFoundError("Preuve introuvable.")
    return proof


async def get_payment_proof_file(
    session: AsyncSession, company_id: uuid.UUID, payment_id: uuid.UUID, proof_id: uuid.UUID
) -> Proof:
    await payment_service.get_payment(session, company_id, payment_id)
    proof = await proof_repository.get_by_id(session, proof_id)
    if proof is None or proof.payment_id != payment_id:
        raise NotFoundError("Preuve introuvable.")
    return proof
