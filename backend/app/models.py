from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Airport(Base):
    __tablename__ = "airports"
    __table_args__ = (
        Index("ix_airports_name", "name"),
        Index("ix_airports_iata_code", "iata_code"),
        Index("ix_airports_municipality", "municipality"),
        Index("ix_airports_icao_code", "icao_code"),
        Index("ix_airports_scheduled_service", "scheduled_service"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    ident: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    latitude_deg: Mapped[float | None] = mapped_column(Float)
    longitude_deg: Mapped[float | None] = mapped_column(Float)
    iso_country: Mapped[str | None] = mapped_column(String(2))
    iso_region: Mapped[str | None] = mapped_column(String)
    municipality: Mapped[str | None] = mapped_column(String)
    scheduled_service: Mapped[bool | None] = mapped_column(Boolean)
    icao_code: Mapped[str | None] = mapped_column(String(4))
    iata_code: Mapped[str | None] = mapped_column(String(3))
