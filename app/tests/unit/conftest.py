import uuid
from dataclasses import dataclass, field

import pytest


@dataclass
class FakeSession:
    _objects: list[object] = field(default_factory=list)

    def add(self, obj: object) -> None:
        self._objects.append(obj)

    async def flush(self) -> None:
        for obj in self._objects:
            if hasattr(obj, "id") and getattr(obj, "id") is None:
                setattr(obj, "id", uuid.uuid4())
        self._objects.clear()

    async def commit(self) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
async def db_session():
    return FakeSession()
