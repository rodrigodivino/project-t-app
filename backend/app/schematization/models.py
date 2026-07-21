import uuid

from sqlalchemy import ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Schematization(Base):
    __tablename__ = "schematization"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspace.id", ondelete="CASCADE"), primary_key=True
    )
    data: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
