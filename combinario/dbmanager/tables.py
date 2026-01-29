from typing import List
from sqlalchemy import String, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column, relationship, Mapped


class Base(DeclarativeBase):
    pass


class Item(Base):
    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    emoji: Mapped[str] = mapped_column(String())
    text: Mapped[str] = mapped_column(String())

    parents: Mapped[List["Parent"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Item(id={self.id!r}, emoji={self.emoji!r}, text={self.text!r})"


class Parent(Base):
    __tablename__ = "parent"
    __table_args__ = (
        UniqueConstraint("item_id", "first", "second"),
        CheckConstraint("first <= second"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first: Mapped[int] = mapped_column()
    second: Mapped[int] = mapped_column()
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"))

    item: Mapped["Item"] = relationship(back_populates="parents")

    def __repr__(self) -> str:
        return f"Parent(id={self.id!r}, first={self.first!r}, second={self.second!r}, item_id={self.item_id!r})"
