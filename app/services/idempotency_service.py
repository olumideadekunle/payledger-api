import json
import hashlib
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyRecord


class IdempotencyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def compute_request_hash(self, endpoint: str, body_dict: dict) -> str:
        serialized = f"{endpoint}:{json.dumps(body_dict, sort_keys=True, default=str)}"
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def get_recorded_response(
        self, key: str, user_id: str
    ) -> Optional[Tuple[int, dict]]:
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.key == key,
            IdempotencyRecord.user_id == user_id,
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if record:
            return record.status_code, json.loads(record.response_data)
        return None

    async def record_response(
        self,
        key: str,
        user_id: str,
        endpoint: str,
        request_hash: str,
        status_code: int,
        response_dict: dict,
    ) -> None:
        record = IdempotencyRecord(
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            request_hash=request_hash,
            status_code=status_code,
            response_data=json.dumps(response_dict, default=str),
        )
        self.db.add(record)
        await self.db.commit()
