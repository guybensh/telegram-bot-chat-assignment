flowchart TB
subgraph app [Application]
main[main.py]
bootstrap[bootstrap.py]
routes[routes]
end

subgraph domain [Domain]
bot[BotService]
chat[ChatService]
end

subgraph providers [messaging_providers]
proto[MessageProvider protocol]
tg[TelegramProvider]
wa[WhatsAppProvider future]
end

bootstrap --> bot
bootstrap --> chat
bootstrap --> proto
tg -.implements.-> proto
chat --> proto
bot --> proto
bootstrap --> ReceiveRuntime[ProviderReceiveRuntime]
ReceiveRuntime --> proto
routes --> chat
routes --> proto
