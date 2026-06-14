def generate_telegram_webhook_url(
        *,
        public_base_url: str,
        webhook_path: str,
        bot_token: str,
) -> str:
    """Build the full URL registered with Telegram's setWebhook."""
    return (
        f"{public_base_url.rstrip('/')}"
        f"{webhook_path.rstrip('/')}/{bot_token}"
    )