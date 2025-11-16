from __future__ import annotations

import io
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, AsyncIterator, Literal, Optional

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .services import scheduling


MessageOrigin = Literal["user", "bot"]

import io
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, AsyncIterator, Literal, Optional

import boto3
import httpx
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .services import scheduling


MessageOrigin = Literal["user", "bot"]
SYSTEM_PROMPT = (
    "Voce e Aurora, atendente virtual de um hospital 100 por cento acessivel. "
    "Mantenha um tom natural, profissional e acolhedor. "
    "Sempre consulte plan_appointment antes de prometer horarios; descreva a disponibilidade de forma simples e cite os medicos livres apenas quando fizer sentido. Se o usúario pedir um horario especifico, verifique com list_available_slots se ha vagas e apenas sugira outro horario se nao houver para o horario desejado. "
    "Se o horário solicitado estiver disponivel, foque apenas nas necessidades do usúario e não sugira ou cite outras datas ou recursos. Se mantenha fiel ao que foi pedido. "
    "Jamais afirme falta de disponibilidade se a consulta à ferramenta indicar vaga; utilize o horario proposto pelo sistema como verdade final. "
    "Se nao houver vagas, explique com empatia e ofereca alternativas."
    "Pergunte sobre preferencia de medico quando apropriado, citando quais estão disponíveis para o horário desejado, mas se a pessoa aceitar um horario (ex.: responder 'pode ser' ou 'combinado'), avance para o registro sem repetir a mesma pergunta. "
    "Nunca pergunte o nível de urgência diretamente, voce deve inferir a partir do que foi relatado, (padrao 2 se nao houver sinais graves ou falta de informação). "
    "Nunca mencione nomes tecnicos de campos/ferramentas; use apenas linguagem natural. "
    "Quando o paciente confirmar, use book_appointment para registrar (uma vez). "
    "A confirmação do agendamento deve ser única e final, após o usúario concordar com o horario sugerido, faça a reserva imediatamente."
    "Na confirmacao final, cite data, horario, especialidade, tipo, recursos acessiveis e o nome do medico de forma amigavel. "
    "Use negrito com **texto** apenas em pontos importantes. "
    "Apos o agendamento, ofereca ajuda adicional ou encerre a conversa educadamente."

)
DEFAULT_GREETING = (
    "Olá! Sou Aurora, atendente virtual inclusiva. Posso ajudar com informações hospitalares acessíveis, "
    "explicar recursos como tradução em Libras ou orientar sobre atendimento para pessoas com deficiência auditiva, "
    "visual ou motora. Como posso apoiar você hoje?"
)


class Message(BaseModel):
    id: int
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


class ProfileData(BaseModel):
    full_name: str
    patient_id: str | None = None
    pronouns: str | None = None
    disabilities: list[str] = Field(default_factory=list)
    accessibility_needs: list[str] = Field(default_factory=list)
    mobility_notes: str | None = None
    contact_preference: str | None = None
    notes: str | None = None


class MessagePayload(BaseModel):
    content: str
    profile: ProfileData | None = None


def profile_to_prompt(profile: dict[str, Any]) -> str:
    parts: list[str] = []
    name = profile.get("full_name")
    if name:
        parts.append(f"Nome: {name}")
    patient_id = profile.get("patient_id")
    if patient_id:
        parts.append(f"Identificador: {patient_id}")
    pronouns = profile.get("pronouns")
    if pronouns:
        parts.append(f"Pronomes: {pronouns}")
    disabilities = profile.get("disabilities") or []
    if disabilities:
        parts.append("Deficiencias: " + ", ".join(disabilities))
    access = profile.get("accessibility_needs") or []
    if access:
        parts.append("Acessibilidades prioritarias: " + ", ".join(access))
    mobility = profile.get("mobility_notes")
    if mobility:
        parts.append(f"Mobilidade/observacoes: {mobility}")
    contact = profile.get("contact_preference")
    if contact:
        parts.append(f"Preferencia de contato: {contact}")
    notes = profile.get("notes")
    if notes:
        parts.append(f"Notas: {notes}")
    summary = "; ".join(parts) if parts else "Perfil basico informado."
    return "Paciente pre-identificado. Considere este contexto sem pedir novamente: " + summary


class SlotAvailabilityPayload(BaseModel):
    specialty: str
    consultation_type: str = "presencial"
    preferred_slot: Optional[str] = None
    accessibility: list[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    days_ahead: int = 7


class BookAppointmentPayload(BaseModel):
    specialty: str
    slot_date: date
    slot: str
    consultation_type: str
    urgency: int = 2
    accessibility: list[str] = Field(default_factory=list)
    doctor_name: str
    triage: Optional[dict[str, Any]] = None


class CapacityPayload(BaseModel):
    date: date
    slot: str


class DoctorStatusPayload(BaseModel):
    doctor_name: str
    date: date
    slot: str


class ResourceStatusPayload(BaseModel):
    date: date
    slot: str


class BookingFilterPayload(BaseModel):
    date: Optional[date] = None
    slot: Optional[str] = None


class CancelBookingPayload(BaseModel):
    booking_id: int


class SuggestSlotPayload(BaseModel):
    specialty: str
    consultation_type: str = "presencial"
    preferred_slot: Optional[str] = None
    accessibility: list[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    days_ahead: int = 14


def _date_to_iso(value: Optional[date]) -> Optional[str]:
    return value.isoformat() if value else None


class LLMServiceError(Exception):
    """Erro interno ao chamar o provedor de LLM."""


def _load_openrouter_api_key() -> str | None:
    direct = os.getenv("OPENROUTER_API_KEY")
    if direct and direct.strip():
        return direct.strip()

    raw = os.getenv("OPENROUTER_API_KEYS")
    if not raw:
        return None

    cleaned = raw.replace("\n", ",").replace(";", ",").split(",")
    keys = [value.strip() for value in cleaned if value.strip()]
    if not keys:
        return None
    return random.choice(keys)


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
        if DEFAULT_GREETING and not self._messages:
            self.add("bot", DEFAULT_GREETING)


def _tool_list_available_slots(**kwargs):
    return scheduling.list_available_slots_tool(kwargs)


def _tool_book_appointment(**kwargs):
    return scheduling.book_appointment(
        specialty=kwargs["specialty"],
        slot_date=kwargs["slot_date"],
        slot=kwargs["slot"],
        consultation_type=kwargs["consultation_type"],
        urgency=int(kwargs.get("urgency", 2)),
        accessibility=kwargs.get("accessibility") or [],
        doctor_name=kwargs["doctor_name"],
        triage=kwargs.get("triage"),
    )


def _tool_triage_score(**kwargs):
    return scheduling.triage_score_tool(kwargs)


def _tool_plan_appointment(**kwargs):
    return scheduling.plan_appointment_tool(kwargs)


def _tool_availability_overview(**kwargs):
    days = int(kwargs.get("days") or 7)
    return {"slots": scheduling.availability_snapshot(days)}


def _tool_slot_overview(**kwargs):
    return scheduling.slot_overview_tool(kwargs["date"])


def _tool_cancel_booking(**kwargs):
    return scheduling.cancel_booking_tool(int(kwargs["booking_id"]))


TOOL_FUNCTIONS: dict[str, Any] = {
    "plan_appointment": _tool_plan_appointment,
    "book_appointment": _tool_book_appointment,
    "availability_overview": _tool_availability_overview,
    "slot_overview": _tool_slot_overview,
    "triage_score": _tool_triage_score,
    "cancel_booking": _tool_cancel_booking,
}

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "plan_appointment",
            "description": "Analisa datas preferidas e retorna o melhor horario encontrado com acessibilidade (ou alternativa).",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {"type": "string"},
                    "consultation_type": {"type": "string", "enum": scheduling.tipo_consulta},
                    "accessibility": {"type": "array", "items": {"type": "string", "enum": scheduling.acessibilidades}},
                    "preferred_slot": {"type": "string", "enum": scheduling.faixas_horarios},
                    "preferred_date": {"type": "string", "description": "Data desejada (YYYY-MM-DD ou DD/MM/YYYY)."},
                    "days_ahead": {"type": "integer", "minimum": 1, "maximum": 30},
                },
                "required": ["specialty"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Registra um agendamento confirmado para a pessoa usuaria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {"type": "string"},
                    "slot_date": {"type": "string", "description": "Data ISO 8601."},
                    "slot": {"type": "string", "enum": scheduling.faixas_horarios},
                    "consultation_type": {"type": "string", "enum": scheduling.tipo_consulta},
                    "urgency": {"type": "integer", "minimum": 1, "maximum": 5},
                    "accessibility": {"type": "array", "items": {"type": "string", "enum": scheduling.acessibilidades}},
                    "doctor_name": {"type": "string"},
                    "triage": {"type": "object"},
                },
                "required": ["specialty", "slot_date", "slot", "consultation_type", "doctor_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "availability_overview",
            "description": "Lista capacidade e recursos restantes por faixa horaria nos proximos dias.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "minimum": 1, "maximum": 30},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slot_overview",
            "description": "Exibe todos os horarios de um dia especifico com capacidade, recursos e medicos livres.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Data em formato ISO (YYYY-MM-DD)."},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "triage_score",
            "description": "Calcula o nivel de urgencia baseado em dados da triagem.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": True},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_booking",
            "description": "Cancela um agendamento existente liberando os recursos associados.",
            "parameters": {
                "type": "object",
                "properties": {
                    "booking_id": {"type": "integer", "minimum": 1},
                },
                "required": ["booking_id"],
            },
        },
    },
]


class STTService:
    """Interface para integrações de Speech-to-Text."""

    def transcribe(
        self,
        audio_blob: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:  # pragma: no cover
        raise NotImplementedError


class AwsSTTService(STTService):
    """Serviço que sobe o áudio para o S3 e usa o Amazon Transcribe."""

    SUPPORTED_MEDIA_FORMATS = {
        "mp3",
        "mp4",
        "wav",
        "flac",
        "ogg",
        "amr",
        "webm",
        "m4a",
    }

    def __init__(
        self,
        *,
        bucket: str,
        region_name: str,
        prefix: str = "",
        language_code: str = "pt-BR",
        output_bucket: str | None = None,
        poll_interval: float = 2.0,
        poll_timeout: float = 180.0,
        job_prefix: str = "chatbot-inclusivo",
    ) -> None:
        self.bucket = bucket
        self.prefix = prefix.strip("/ ")
        self.language_code = language_code
        self.output_bucket = output_bucket
        self.poll_interval = poll_interval
        self.poll_timeout = poll_timeout
        self.job_prefix = job_prefix
        self.s3_client = boto3.client("s3", region_name=region_name)
        self.transcribe_client = boto3.client("transcribe", region_name=region_name)

    def transcribe(
        self,
        audio_blob: bytes,
        filename: str | None = None,
        content_type: str | None = None,
    ) -> str:
        if not audio_blob:
            raise ValueError("O arquivo de áudio está vazio.")

        media_format = self._infer_media_format(filename)
        object_key = self._build_object_key(media_format)

        upload_stream = io.BytesIO(audio_blob)
        upload_stream.seek(0)

        extra_args = {"ContentType": content_type} if content_type else None

        if extra_args:
            self.s3_client.upload_fileobj(upload_stream, self.bucket, object_key, ExtraArgs=extra_args)
        else:
            self.s3_client.upload_fileobj(upload_stream, self.bucket, object_key)

        job_name = f"{self.job_prefix}-{uuid.uuid4()}"
        job_args: dict[str, object] = {
            "TranscriptionJobName": job_name,
            "LanguageCode": self.language_code,
            "MediaFormat": media_format,
            "Media": {"MediaFileUri": f"s3://{self.bucket}/{object_key}"},
        }
        if self.output_bucket:
            job_args["OutputBucketName"] = self.output_bucket

        self.transcribe_client.start_transcription_job(**job_args)
        return self._poll_until_finished(job_name)

    def _poll_until_finished(self, job_name: str) -> str:
        deadline = time.monotonic() + self.poll_timeout

        while time.monotonic() < deadline:
            job = self.transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = job["TranscriptionJob"]["TranscriptionJobStatus"]

            if status == "COMPLETED":
                transcript_url = job["TranscriptionJob"]["Transcript"].get(
                    "TranscriptFileUri"
                )
                if not transcript_url:
                    raise RuntimeError("Transcribe finalizou sem gerar transcript.")
                return self._download_transcript(transcript_url)

            if status == "FAILED":
                failure_reason = job["TranscriptionJob"].get("FailureReason", "motivo desconhecido")
                raise RuntimeError(f"Transcribe falhou: {failure_reason}")

            time.sleep(self.poll_interval)

        raise TimeoutError(f"Transcrição não finalizada dentro de {self.poll_timeout} segundos.")

    def _download_transcript(self, url: str) -> str:
        response = httpx.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()
        transcripts = payload.get("results", {}).get("transcripts", [])
        if not transcripts:
            raise RuntimeError("Transcrição vazia retornada pela AWS.")
        return transcripts[0].get("transcript", "").strip()

    def _infer_media_format(self, filename: str | None) -> str:
        if filename and "." in filename:
            candidate = filename.rsplit(".", 1)[1].lower()
            if candidate in self.SUPPORTED_MEDIA_FORMATS:
                return candidate
        return "wav"

    def _build_object_key(self, extension: str) -> str:
        object_name = f"{uuid.uuid4()}.{extension}"
        if self.prefix:
            return f"{self.prefix}/{object_name}"
        return object_name



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
        self._api_keys: list[str] = []
        if api_key:
            self._api_keys = [api_key]
        self._client = self._build_client(api_key)
        self.tools = TOOL_DEFINITIONS

    def _build_client(self, api_key: str | None) -> AsyncOpenAI | None:
        if not api_key:
            return None
        return AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _pick_new_key(self) -> bool:
        raw = os.getenv("OPENROUTER_API_KEYS")
        entries: list[str] = []
        if raw:
            entries = [item.strip() for item in raw.replace("\n", ",").replace(";", ",").split(",") if item.strip()]
        direct = os.getenv("OPENROUTER_API_KEY")
        if direct and direct.strip():
            entries.append(direct.strip())
        unique = [key for idx, key in enumerate(entries) if key and key not in entries[:idx]]
        if not unique:
            return False
        choice = random.choice(unique)
        self._client = self._build_client(choice)
        return self._client is not None

    def _build_messages(self, history: list[Message], profile: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        today = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
        messages.append({"role": "system", "content": f"Data atual: {today}. Use esta data como referencia."})
        if profile:
            messages.append({"role": "system", "content": profile_to_prompt(profile)})
        for message in history:
            role = "assistant" if message.origin == "bot" else "user"
            messages.append({"role": role, "content": message.content})
        return messages

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        func = TOOL_FUNCTIONS.get(name)
        if not func:
            return {"error": f"Ferramenta {name} nao disponivel."}
        return await run_in_threadpool(func, **args)

    async def _call_model(self, messages: list[dict[str, Any]]):
        client = self._client
        if not client:
            raise LLMServiceError("LLM nao configurado.")
        try:
            return await client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                },
            )
        except Exception as exc:  # pragma: no cover
            raise LLMServiceError("Falha ao chamar o provedor de LLM") from exc

    async def _run_with_tools(self, messages: list[dict[str, Any]]) -> str:
        while True:
            try:
                response = await self._call_model(messages)
            except LLMServiceError as exc:
                logger.warning("LLM indisponivel: %s", exc)
                if self._pick_new_key():
                    logger.info("Trocando chave OpenRouter e tentando novamente.")
                    continue
                return "Desculpe, o provedor de respostas esta indisponivel agora. Tente novamente em instantes."
            if not response.choices:
                return "Desculpe, nao consegui gerar uma resposta agora."
            choice = response.choices[0]
            message = choice.message
            if getattr(message, "tool_calls", None):
                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": call.type,
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in message.tool_calls
                    ],
                }
                messages.append(assistant_message)
                for call in message.tool_calls:
                    try:
                        args = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}
                    result = await self._execute_tool(call.function.name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.function.name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                continue
            if message.content:
                reply = message.content.strip()
                if reply:
                    messages.append({"role": "assistant", "content": reply})
                    return reply
            return "Desculpe, nao consegui gerar uma resposta agora."

    async def _stream_with_tools(self, messages: list[dict[str, Any]]) -> AsyncIterator[str]:
        try:
            client = self._client
            if not client:
                raise LLMServiceError("LLM nao configurado.")
            stream = await client.chat.completions.create(
                model=self.model,
                stream=True,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                extra_headers={
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                },
            )
            assistant_text = ""
            tool_calls: dict[str, dict[str, Any]] = {}
            finish_reason = None

            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                finish_reason = choice.finish_reason
                delta = choice.delta
                content = delta.content
                if isinstance(content, list):
                    for piece in content:
                        text = None
                        if isinstance(piece, str):
                            text = piece
                        elif isinstance(piece, dict) and piece.get("type") == "text":
                            text = piece.get("text")
                        if text:
                            assistant_text += text
                            yield text
                elif isinstance(content, str):
                    assistant_text += content
                    yield content

                if delta.tool_calls:
                    for call in delta.tool_calls:
                        entry = tool_calls.setdefault(
                            call.id,
                            {"id": call.id, "type": call.type, "function": {"name": "", "arguments": ""}},
                        )
                        if call.function and call.function.name:
                            entry["function"]["name"] = call.function.name
                        if call.function and call.function.arguments:
                            entry["function"]["arguments"] += call.function.arguments

            if tool_calls and finish_reason == "tool_calls":
                assistant_message = {
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_calls": [
                        {
                            "id": call_id,
                            "type": data["type"],
                            "function": data["function"],
                        }
                        for call_id, data in tool_calls.items()
                    ],
                }
                messages.append(assistant_message)
                for call_id, data in tool_calls.items():
                    func_name = data["function"].get("name") or ""
                    args_json = data["function"].get("arguments") or "{}"
                    try:
                        args = json.loads(args_json)
                    except json.JSONDecodeError:
                        args = {}
                    result = await self._execute_tool(func_name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call_id,
                            "name": func_name,
                            "content": json.dumps(result, ensure_ascii=False),
                        }
                    )
                final_reply = await self._run_with_tools(messages)
                if assistant_text and final_reply.startswith(assistant_text):
                    tail = final_reply[len(assistant_text):]
                else:
                    tail = final_reply
                if tail:
                    yield tail
                elif final_reply:
                    yield final_reply
                return
        except Exception as exc:  # pragma: no cover
            logger.exception("Falha no stream do OpenRouter: %s", exc)
            yield "Desculpe, nao consegui falar com o modelo agora. Tente novamente."

    async def generate_reply(self, history: list[Message], profile: dict[str, Any] | None = None) -> str:
        if not self._client:
            return "Echo acessivel: configure OPENROUTER_API_KEY para usar respostas reais."
        messages = self._build_messages(history, profile)
        return await self._run_with_tools(messages)

    async def stream_reply(self, history: list[Message], profile: dict[str, Any] | None = None) -> AsyncIterator[str]:
        if not self._client:
            fallback = "Echo acessivel: configure OPENROUTER_API_KEY para usar respostas reais."
            for char in fallback:
                yield char
            return

        messages = self._build_messages(history, profile)
        reply = await self._run_with_tools(messages)
        step = 12
        for idx in range(0, len(reply), step):
            yield reply[idx : idx + step]


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("chatbot-inclusivo")

store = InMemoryMessageStore()
orchestrator = LLMOrchestrator(
    api_key=_load_openrouter_api_key(),
    model=os.getenv("OPENROUTER_MODEL", "qwen/qwen3-235b-a22b:free"),
    site_url=os.getenv("OPENROUTER_SITE_URL", "http://localhost:5173"),
    app_name=os.getenv("OPENROUTER_APP_NAME", "Chatbot Inclusivo"),
)
stt_service: STTService | None = None


def _build_stt_service() -> STTService | None:
    bucket = os.getenv("AWS_S3_BUCKET")
    region = os.getenv("AWS_REGION")
    if not bucket or not region:
        logger.info("Serviço de STT não configurado (bucket ou região ausentes).")
        return None

    prefix = os.getenv("AWS_S3_PREFIX", "stt").strip()
    language = os.getenv("AWS_TRANSCRIBE_LANGUAGE", "pt-BR")
    output_bucket = os.getenv("AWS_TRANSCRIBE_OUTPUT_BUCKET") or None

    try:
        return AwsSTTService(
            bucket=bucket,
            region_name=region,
            prefix=prefix,
            language_code=language,
            output_bucket=output_bucket,
        )
    except Exception as exc:  # pragma: no cover - falha de inicialização
        logger.exception("Falha ao configurar o serviço de STT: %s", exc)
        return None


stt_service = _build_stt_service()

app = FastAPI(title="Chatbot Inclusivo API", version="0.1.0")

allowed_origins_env = os.getenv("ALLOW_ORIGINS")
if allowed_origins_env:
    origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    origins = [
        "http://localhost:5173",
        "http://localhost:4173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
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
    profile_data = payload.profile.model_dump() if payload.profile else None
    reply = await orchestrator.generate_reply(store.history(), profile_data)
    store.add("bot", reply)
    return store.history()


@app.post("/messages/stream")
async def post_message_stream(payload: MessagePayload):
    store.add("user", payload.content)

    async def token_stream():
        bot_content = ""
        profile_data = payload.profile.model_dump() if payload.profile else None
        async for token in orchestrator.stream_reply(store.history(), profile_data):
            bot_content += token
            yield token
        store.add("bot", bot_content)

    return StreamingResponse(token_stream(), media_type="text/plain")


@app.post("/transcriptions")
async def create_transcription(file: UploadFile = File(...)):
    if not stt_service:
        raise HTTPException(
            status_code=503,
            detail="Serviço de transcrição não configurado. Informe as variáveis da AWS.",
        )

    audio_blob = await file.read()
    if not audio_blob:
        raise HTTPException(status_code=400, detail="O arquivo de áudio está vazio.")

    try:
        transcript = await run_in_threadpool(
            stt_service.transcribe,
            audio_blob,
            file.filename,
            file.content_type,
        )
        return {"transcript": transcript}
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except (BotoCoreError, ClientError) as exc:
        logger.exception("Falha ao comunicar com AWS STT: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Falha ao processar o áudio via AWS Transcribe.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover
        logger.exception("Erro inesperado ao transcrever áudio: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Erro inesperado ao transcrever o áudio.",
        ) from exc

@app.post("/tools/slots")
async def list_slots(payload: SlotAvailabilityPayload):
    data = payload.model_dump()
    data["start_date"] = _date_to_iso(payload.start_date)
    return scheduling.list_available_slots_tool(data)


@app.post("/tools/book")
async def create_booking(payload: BookAppointmentPayload):
    try:
        result = scheduling.book_appointment(
            specialty=payload.specialty,
            slot_date=payload.slot_date.isoformat(),
            slot=payload.slot,
            consultation_type=payload.consultation_type,
            urgency=payload.urgency,
            accessibility=payload.accessibility,
            doctor_name=payload.doctor_name,
            triage=payload.triage,
        )
        return result
    except Exception as exc:  # pragma: no cover
        logger.exception("Falha ao criar agendamento: %s", exc)
        raise HTTPException(status_code=500, detail="Nao foi possivel registrar o agendamento.") from exc


@app.post("/tools/capacity")
async def check_capacity(payload: CapacityPayload):
    return scheduling.check_capacity_tool(payload.date.isoformat(), payload.slot)


@app.post("/tools/doctor-status")
async def doctor_status(payload: DoctorStatusPayload):
    return scheduling.doctor_status_tool(payload.doctor_name, payload.date.isoformat(), payload.slot)


@app.post("/tools/resources")
async def resources_status(payload: ResourceStatusPayload):
    return scheduling.resources_status_tool(payload.date.isoformat(), payload.slot)


@app.post("/tools/triage-score")
async def calc_triage(payload: dict[str, Any]):
    return scheduling.triage_score_tool(payload)


@app.post("/tools/bookings")
async def list_bookings_endpoint(payload: BookingFilterPayload):
    return scheduling.list_bookings_tool(
        date_str=_date_to_iso(payload.date),
        faixa=payload.slot,
    )


@app.get("/tools/patients/{patient_id}")
async def get_patient_requirements(patient_id: int):
    data = scheduling.patient_requirements_tool(patient_id)
    if not data:
        raise HTTPException(status_code=404, detail="Paciente nao encontrado.")
    return data


@app.post("/tools/cancel-booking")
async def cancel_booking_endpoint(payload: CancelBookingPayload):
    result = scheduling.cancel_booking_tool(payload.booking_id)
    if not result.get("cancelled"):
        raise HTTPException(status_code=404, detail=result.get("reason", "Agendamento nao encontrado."))
    return result


@app.post("/tools/suggest-slot")
async def suggest_slot(payload: SuggestSlotPayload):
    data = payload.model_dump()
    data["start_date"] = _date_to_iso(payload.start_date)
    return scheduling.suggest_alternative_slot_tool(data)


@app.get("/availability")
async def get_availability(days: int = 7):
    safe_days = max(1, min(days, 30))
    return scheduling.availability_snapshot(safe_days)
