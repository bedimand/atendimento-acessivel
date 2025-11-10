from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator, Literal

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel


MessageOrigin = Literal["user", "bot"]
SYSTEM_PROMPT = (
    "Você é Aurora, atendente virtual de um hospital 100% acessível. "
    "Ofereça acolhimento inclusivo para pessoas com deficiência auditiva, visual ou motora, "
    "informe recursos como tradução em Libras, leitura otimizada e integração com sistemas hospitalares. "
    "Use linguagem simples, empática e descreva ações de forma clara. "
    "Sempre se apresente como Aurora e lembre o usuário de que está pronta para adaptar o atendimento."
)
DEFAULT_GREETING = (
    "Olá! Sou Aurora, atendente virtual inclusiva. Posso ajudar com informações hospitalares acessíveis, "
    "explicar recursos como tradução em Libras ou orientar sobre atendimento para pessoas com deficiência auditiva, "
    "visual ou motora. Como posso apoiar você hoje?"
)


class Message(BaseModel):
    id: int
    origin: MessageOrigin
    content: str
    created_at: datetime


class MessagePayload(BaseModel):
    content: str


@dataclass
class InMemoryMessageStore:
    _messages: list[Message] = field(default_factory=list)
    _counter: int = 1

    def add(self, origin: MessageOrigin, content: str) -> Message:
        message = Message(
            id=self._counter,
            origin=origin,
            content=content,
            created_at=datetime.now(timezone.utc),
        )
        self._counter += 1
        self._messages.append(message)
        return message

    def history(self) -> list[Message]:
        return list(self._messages)

    def __post_init__(self) -> None:
        if not self._messages:
            self.add("bot", DEFAULT_GREETING)


class STTService:
    """Placeholder for future Speech-to-Text integrations."""

    def transcribe(self, audio_blob: bytes) -> str:  # pragma: no cover
        raise NotImplementedError


class LLMOrchestrator:
    """Wrapper para chamadas ao OpenRouter utilizando o SDK OpenAI."""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        site_url: str,
        app_name: str,
    ) -> None:
        self.model = model
        self.site_url = site_url
        self.app_name = app_name
        self.client = (
            AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            if api_key
            else None
        )

    async def generate_reply(self, text: str) -> str:
        if not self.client:
            return (
                "Echo acessível: configure OPENROUTER_API_KEY para usar respostas reais."
            )

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                        SYSTEM_PROMPT
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                },
                extra_body={},
            )
            if completion.choices:
                return completion.choices[0].message.content.strip()
            return "Desculpe, não consegui gerar uma resposta agora."
        except Exception as exc:
            logger.exception("Falha ao consultar OpenRouter: %s", exc)
            return "Desculpe, não consegui falar com o modelo agora. Tente novamente."

    async def stream_reply(self, text: str) -> AsyncIterator[str]:
        if not self.client:
            fallback = "Echo acessível: configure OPENROUTER_API_KEY para usar respostas reais."
            for char in fallback:
                yield char
            return

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                stream=True,
                messages=[
                    {
                        "role": "system",
                        "content": (
                        SYSTEM_PROMPT
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                },
                extra_body={},
            )

            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as exc:  # pragma: no cover
            logger.exception("Falha no stream do OpenRouter: %s", exc)
            yield "Desculpe, não consegui falar com o modelo agora. Tente novamente."


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot-inclusivo")

store = InMemoryMessageStore()
orchestrator = LLMOrchestrator(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    model=os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-20b:free"),
    site_url=os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173"),
    app_name=os.getenv("OPENROUTER_APP_NAME", "Chatbot Inclusivo"),
)

app = FastAPI(title="Chatbot Inclusivo API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/history", response_model=list[Message])
async def get_history() -> list[Message]:
    return store.history()


@app.post("/messages", response_model=list[Message])
async def post_message(payload: MessagePayload) -> list[Message]:
    store.add("user", payload.content)
    reply = await orchestrator.generate_reply(payload.content)
    store.add("bot", reply)
    return store.history()


@app.post("/messages/stream")
async def post_message_stream(payload: MessagePayload):
    store.add("user", payload.content)

    async def token_stream():
        bot_content = ""
        async for token in orchestrator.stream_reply(payload.content):
            bot_content += token
            yield token
        store.add("bot", bot_content)

    return StreamingResponse(token_stream(), media_type="text/plain")
