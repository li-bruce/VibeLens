"""SQLAlchemy schema and transactional persistence for the runnable gallery."""

from contextlib import nullcontext
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    Table,
    insert,
    select,
    update,
)

metadata = MetaData()
artwork = Table(
    "artwork",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("image_version", Integer, nullable=False),
    Column("status", String, nullable=False),
)
images = Table(
    "images",
    metadata,
    Column("version", Integer, primary_key=True),
    Column("title", String, nullable=False),
    Column("content", LargeBinary),
)
messages = Table(
    "messages",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("image_version", Integer, ForeignKey("images.version")),
    Column("text", String, nullable=False),
)
exhibition = Table(
    "exhibition",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("image_version", Integer, ForeignKey("images.version")),
)


class Repository:
    """Expose narrow operations; observer metadata reads use separate connections."""

    def __init__(self, engine, observer=None):
        self.engine, self.bo = engine, observer
        metadata.create_all(engine)
        with engine.begin() as connection:
            if connection.execute(select(artwork.c.id)).first() is None:
                connection.execute(
                    insert(artwork), {"id": 1, "image_version": 0, "status": "empty"}
                )

    def operation(self, name, parameters=None):
        return self.bo.operation(name, parameters or {}) if self.bo else nullcontext()

    def read_artwork(self, connection=None):
        """Read the authoritative version and state without reconstructing it from traces."""
        with self.operation("read-artwork"):
            if connection is not None:
                return dict(connection.execute(select(artwork)).mappings().one())
            with self.engine.connect() as current:
                return dict(current.execute(select(artwork)).mappings().one())

    def save_upload(self, title, raw):
        """Store a replacement and its notification together, retaining old image bytes."""
        with self.operation("save-upload"), self.engine.begin() as connection:
            current = connection.execute(select(artwork.c.image_version)).scalar_one() + 1
            connection.execute(insert(images), {"version": current, "title": title, "content": raw})
            connection.execute(update(artwork).values(image_version=current, status="pending"))
            connection.execute(
                insert(messages), {"image_version": current, "text": "Ready for review"}
            )
            return current

    def publish(self, connection, selected):
        """Persist the selected image version and its public state in the same transaction."""
        with self.operation("save-exhibition", {"selected": selected}):
            existing = connection.execute(select(exhibition.c.id)).first()
            if existing:
                connection.execute(update(exhibition).values(image_version=selected))
            else:
                connection.execute(insert(exhibition), {"id": 1, "image_version": selected})
            connection.execute(update(artwork).values(status="displayed"))

    def public(self):
        """Return public image identity and reviewer messages through real SQL queries."""
        with self.operation("read-public"), self.engine.connect() as connection:
            published = connection.execute(select(exhibition.c.image_version)).scalar()
            notices = list(connection.execute(select(messages.c.image_version)).scalars())
            return {"published_version": published, "messages": notices}

    def image(self, version):
        with self.operation("read-image"), self.engine.connect() as connection:
            return connection.execute(
                select(images.c.content).where(images.c.version == version)
            ).scalar()
