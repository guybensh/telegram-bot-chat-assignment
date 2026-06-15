from pydantic import BaseModel, computed_field


class BotRecord(BaseModel):
    """Registered bot profile. Tokens are stored separately in the repository.

    `username` is unique across all registered bots (enforced by the repository).
    """

    bot_id: str
    bot_name: str
    username: str  # unique — used in API paths (`/bots/{username}/...`)
    max_chats: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def private(self) -> bool:
        """Single-user bot (max_chats == 1). UI indicator only."""
        return self.max_chats == 1


class BotInboxItem(BotRecord):
    """Bot row for the inbox sidebar, including live capacity usage."""

    active_chats: int
