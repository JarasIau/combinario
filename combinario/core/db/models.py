from typing import List
from sqlalchemy import String, ForeignKey, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, Mapped
from sqlalchemy.ext.asyncio import AsyncAttrs


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    parents: Mapped[List["Parent"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, emoji={self.emoji!r}, text={self.text!r})"


class Parent(Base):
    __tablename__ = "parent"
    __table_args__ = (
        UniqueConstraint("item_id", "first", "second"),
        UniqueConstraint("first", "second", name="uq_parent_first_second"),
        CheckConstraint("first <= second"),  # just a safety net
        Index("idx_first_second", "first", "second"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first: Mapped[int] = mapped_column(nullable=False)
    second: Mapped[int] = mapped_column(nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)

    item: Mapped["Item"] = relationship(back_populates="parents")

    def __repr__(self) -> str:
        return f"Parent(id={self.id!r}, first={self.first!r}, second={self.second!r}, item_id={self.item_id!r})"
