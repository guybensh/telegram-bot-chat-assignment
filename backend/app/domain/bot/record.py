from pydantic import BaseModel, computed_field


class BotRecord(BaseModel):
    """Registered bot profile. Tokens are stored separately in the repository."""

    bot_id: str
    bot_name: str
    username: str
    max_chats: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def private(self) -> bool:
        """Single-user bot (max_chats == 1). UI indicator only."""
        return self.max_chats == 1


class BotInboxItem(BotRecord):
    """Bot row for the inbox sidebar, including live capacity usage."""

    active_chats: int
