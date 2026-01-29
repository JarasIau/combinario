from tables import Item, Parent
from sqlalchemy import create_engine, select, inspect
from sqlalchemy.orm import Session


class DBManager:
    def __init__(self, db_path: str):
        self.engine = create_engine(f"sqlite://{db_path}", echo=True)

        if not self._tables_exist():
            from tables import Base
            Base.metadata.create_all(self.engine)

    def close(self):
        self.engine.dispose()

    def add_item(self, text: str, emoji: str, parents: list[tuple[int, int]]) -> int:
        with Session(self.engine) as session:
            item = Item(emoji=emoji, text=text)
            for first, second in parents:
                parent = Parent(first=first, second=second)
                item.parents.append(parent)
            session.add(item)
            session.commit()
            return item.id

    def add_parent(self, item_id: int, first: int, second: int) -> bool:
        with Session(self.engine) as session:
            item = session.get(Item, item_id)
            if item:
                parent = Parent(first=first, second=second)
                item.parents.append(parent)
                session.commit()
                return True
            return False

    def query(self, first: int, second: int) -> Item | None:
        with Session(self.engine) as session:
            stmt = (
                select(Item)
                .join(Item.parents)
                .where(Parent.first == first, Parent.second == second)
            )
            return session.execute(stmt).scalar_one_or_none()

    def _tables_exist(self) -> bool:
        inspector = inspect(self.engine)
        existing = inspector.get_table_names()
        required = {"item", "parent"}
        return required.issubset(existing)