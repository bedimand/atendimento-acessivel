# Chatbot Inclusivo – Plano de Desenvolvimento

Plano usado por agentes de código (Codex / afins) como especificação viva.

---

## 1. Objetivo geral

Construir um chatbot acessível, estilo ChatGPT, com:

- Frontend em **React + TypeScript + Vite**.
- Backend em **Python + FastAPI**.
- Suporte a mensagens de texto e áudio (gravação + STT futuro).
- TTS via `window.speechSynthesis`.
- Integração do **VLibras**.
- Arquitetura preparada para futura orquestração de agentes/LLMs.

---

## 2. Escopo da primeira entrega (MVP 0.1 – esqueleto funcional)

### 2.1 Frontend (React + TS + Vite)

- Layout base estilo chat (lista rolável + input fixo).
- Componentes: histórico, campo de texto, botão enviar, botão gravação estilo WhatsApp, botão TTS, widget VLibras.
- Integrações: script oficial VLibras, placeholder de gravação de áudio (sem upload), TTS simples com `window.speechSynthesis`.

### 2.2 Backend (Python + FastAPI)

- `POST /messages` para texto (futuro: áudio).
- `GET /history` para histórico.
- Interfaces preparadas para `STTService` e orquestrador LLM (mock).
- Persistência em memória (lista) para testes.

### 2.3 Fluxo de dados

1. Frontend envia mensagem para `POST /messages`.
2. Backend armazena mensagem, gera eco acessível (`Echo acessivel: <texto>`), armazena resposta.
3. Backend retorna histórico completo.
4. Frontend renderiza histórico, permite TTS e mostra controles de áudio + VLibras.

---

## 3. Arquitetura geral

```text
chatbot-inclusivo/
  frontend/        # React + TS + Vite
  backend/         # FastAPI + Pydantic
  docs/            # Arquitetura, acessibilidade, etc.
```

---

## 4. Cronograma e marcos

| Semana | Marco | Entregáveis |
| --- | --- | --- |
| S1 | Setup base | Repositórios frontend/backend, lint, CI rápida, documento de acessibilidade inicial |
| S2 | MVP frontend | Layout chat, componentes principais, VLibras embedado, stub de gravação |
| S3 | MVP backend | Endpoints `messages` e `history`, mock de respostas, testes básicos |
| S4 | Integração | Fluxo ponta a ponta texto → resposta, TTS acionável, demo interna |
| S5 | Refinos | Ajustes de UX/acessibilidade, documentação de uso, backlog MVP 0.2 |

---

## 5. Backlog detalhado

### 5.1 MVP 0.1

- **Infra**: criar monorepo (ou dois repositórios coordenados), configurar lint/format (ESLint, Prettier, Ruff), scripts de dev.
- **Frontend**:
  - Estrutura de estado global simples (Context API) para histórico.
  - Componentes `ChatWindow`, `MessageList`, `MessageInput`, `AudioRecorderButton`, `TTSButton`, `VLibrasWidget`.
  - Serviço `apiClient` encapsulando chamadas a `/messages` e `/history`.
  - Hook `useSpeechSynthesis` com fallback quando API não existir.
- **Backend**:
  - Modelo `Message { id, origin(user|bot), content, created_at }`.
  - Serviço em memória `InMemoryMessageStore`.
  - Classe `LLMOrchestrator` mock retornando eco.
  - Estrutura de interfaces `STTService` e `AudioStorage`.
  - Testes unitários FastAPI para endpoints.
- **Docs**: instruções de setup, guia rápido de acessibilidade (contraste, navegação teclado, uso VLibras).

### 5.2 MVP 0.2 (pré-integração de voz real)

- Upload de áudio do frontend para backend (armazenamento temporário local).
- Endpoint dedicado `POST /audio` chamando `STTService` fake.
- Seleção de vozes TTS e controle de velocidade.
- Persistência opcional em SQLite para histórico.
- Automatizar deploy do backend (Railway/Fly.io) e frontend (Vercel/Netlify).

### 5.3 MVP 0.3 (quando Azure STT estiver disponível)

- Integração real com Azure Speech to Text (token seguro via backend).
- Painel simples de administração para rever conversas.
- Suporte a múltiplos usuários (IDs de sessão no frontend).
- Avaliação de LLM externo (Azure OpenAI / Open-source local) com camada de ferramentas.

---

## 6. Dependências e integrações

- **VLibras**: script oficial via `<script src="https://vlibras.gov.br/app/vlibras-plugin.js">`.
- **TTS**: `window.speechSynthesis` + verificação de disponibilidade em `navigator`.
- **STT futuro**: Azure Speech to Text (configurar `AZURE_SPEECH_KEY`, `AZURE_REGION` em `.env` backend).
- **Hospedagem**: containers Docker (docker-compose) para facilitar deploy.
- **CI/CD**: GitHub Actions com lint + testes (gatilho pull request).

---

## 7. Qualidade, acessibilidade e métricas

- **Acessibilidade**:
  - Conformidade mínima WCAG 2.1 AA (foco visível, contraste 4.5:1, navegação teclado).
  - Labels para controles de áudio, descrição para ícones.
  - Testes com leitores de tela (NVDA/VoiceOver) antes de liberar MVP.
- **Qualidade**:
  - ESLint + TypeScript strict no frontend.
  - Ruff + pytest no backend.
  - Storybook opcional para validar componentes acessíveis.
- **Métricas iniciais**:
  - Tempo de resposta médio backend.
  - Nº de sessões/dia (contador simples em memória).
  - Uso de TTS vs texto (event tracking básico no frontend).

---

## 8. Riscos e mitigação

- **Integração STT demorada** → manter contrato `STTService` e mocks para não bloquear frontend.
- **Complexidade de acessibilidade** → criar checklist por PR e rodar Lighthouse + axe.
- **Persistência em memória limitada** → planejar migração para SQLite/Postgres antes de pilotos reais.
- **TTS não suportado em todos navegadores** → detectar suporte e exibir fallback (download da transcrição).

---

## 9. Próximos passos imediatos

1. Consolidar monorepo com `frontend/` e `backend/`.
2. Gerar scaffolding Vite (React + TS) e FastAPI com Poetry.
3. Configurar lint/test/CI mínimos.
4. Implementar fluxos do MVP 0.1 seguindo backlog.
