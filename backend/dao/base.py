from sqlalchemy.ext.asyncio import AsyncSession


class BaseDAO:
    """..."""

    def __init__(self, session: AsyncSession):
        self.session = session
