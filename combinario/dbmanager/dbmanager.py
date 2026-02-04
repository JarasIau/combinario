from .tables import Item, Parent
from .schemas import ItemSchema, ParentSchema
from sqlalchemy import create_engine, select, inspect
from sqlalchemy.orm import Session


class DBManager:
    def __init__(self, db_path: str):
        self.engine = create_engine(db_path, echo=True)

        if not self._tables_exist():
            from .tables import Base

            Base.metadata.create_all(self.engine)

    def close(self):
        self.engine.dispose()

    def add_item(self, item_data: ItemSchema) -> int:
        with Session(self.engine) as session:
            item = Item(emoji=item_data.emoji, text=item_data.text)
            for parent_data in item_data.parents:
                first, second = sorted((parent_data.first, parent_data.second))
                parent = Parent(first=first, second=second)
                item.parents.append(parent)
            session.add(item)
            session.commit()
            session.refresh(item)
            return item.id

    def add_parent(self, parent_data: ParentSchema) -> bool:
        with Session(self.engine) as session:
            item = session.get(Item, parent_data.item_id)
            if item:
                parent = Parent(first=parent_data.first, second=parent_data.second)
                item.parents.append(parent)
                session.commit()
                return True
            return False

    def query_item(self, item_id: int) -> Item | None:
        with Session(self.engine) as session:
            stmt = select(Item).where(Item.id == item_id)
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                session.refresh(result, ["parents"])
            return result

    def query_by_parents(self, parent_data: ParentSchema) -> Item | None:
        with Session(self.engine) as session:
            first, second = sorted((parent_data.first, parent_data.second))
            stmt = (
                select(Item)
                .join(Item.parents)
                .where(
                    Parent.first == first,
                    Parent.second == second,
                )
            )
            result = session.execute(stmt).scalar_one_or_none()
            if result:
                session.refresh(result, ["parents"])
            return result

    def _tables_exist(self) -> bool:
        inspector = inspect(self.engine)
        existing = inspector.get_table_names()
        required = {"item", "parent"}
        return required.issubset(existing)
