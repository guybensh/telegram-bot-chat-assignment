def generate_telegram_webhook_url(
    *,
    public_base_url: str,
    webhook_path: str,
    bot_id: str,
) -> str:
    """Build the full URL registered with Telegram's setWebhook."""
    return f"{public_base_url.rstrip('/')}{webhook_path.rstrip('/')}/{bot_id}"
