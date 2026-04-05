1. app/schemas_DTO/ai.py

  在現有內容下面加：

  class ChatRequest(BaseModel):
      message: str
      conversation_id: Optional[str] = None      # None = 新對話
      destinations: Optional[list[str]] = None
      use_web_search: bool = True
      show_thinking: bool = False

  不需要 response schema，SSE 直接 stream。

  ---
  2. app/services/ai_service.py

  加 import 和新函數 chat_ai()：

  import re
  import json
  import uuid
  from typing import Generator

  def chat_ai(
      user_id: str,
      message: str,
      conversation_id: str | None,
      destinations: list[str] | None,
      use_web_search: bool,
      show_thinking: bool,
  ) -> Generator:
      """
      Streaming chat with conversation history stored in Redis
      """
      from app.db.redis import get_redis

      redis = get_redis()
      conv_id = conversation_id or str(uuid.uuid4())
      history_key = f"chat:{user_id}:{conv_id}"

      # Load conversation history from Redis
      history = []
      if redis:
          raw = redis.get(history_key)
          if raw:
              history = json.loads(raw)

      # CAG: user context
      cag_ctx = build_user_context(user_id)
      system_prompt = build_system_prompt(cag_ctx)

      # Show thinking instruction
      if show_thinking:
          system_prompt += (
              "\n\nBefore answering, wrap your reasoning inside <thinking>...</thinking> tags. "
              "Then provide your final answer outside the tags."
          )

      # RAG: only if destinations provided
      rag_text = ""
      if use_web_search and destinations and settings.TAVILY_API_KEY:
          rag_text = retrieve_place_context(destinations, message)

      user_message = build_user_message(message, rag_text)

      # Build full messages array
      messages = [{"role": "system", "content": system_prompt}]
      messages.extend(history)
      messages.append({"role": "user", "content": user_message})

      client = get_llm_client()
      stream = client.chat.completions.create(
          model=settings.LLM_MODEL,
          max_tokens=4096,
          messages=messages,
          stream=True,
      )

      # Stream and collect full response
      def generate():
          # First event: send conversation_id
          yield f"data: {json.dumps({'type': 'meta', 'conversation_id': conv_id})}\n\n"

          full_content = ""
          thinking_sent = False

          for chunk in stream:
              delta = chunk.choices[0].delta.content or ""
              full_content += delta

              # If show_thinking: buffer until </thinking> is found, then switch to token
              if show_thinking and not thinking_sent:
                  if "</thinking>" in full_content:
                      match = re.search(r"<thinking>(.*?)</thinking>", full_content, re.DOTALL)
                      if match:
                          thinking_text = match.group(1).strip()
                          yield f"data: {json.dumps({'type': 'thinking', 'content': thinking_text})}\n\n"
                          # Stream everything after </thinking> as tokens
                          remainder = full_content[match.end():].strip()
                          if remainder:
                              yield f"data: {json.dumps({'type': 'token', 'content': remainder})}\n\n"
                          thinking_sent = True
                  # Still buffering, don't yield yet
                  continue

              if delta:
                  yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"

          # Save updated history to Redis
          if redis:
              history.append({"role": "user", "content": user_message})
              history.append({"role": "assistant", "content": full_content})
              # Keep last 20 messages to avoid token overflow
              trimmed = history[-20:]
              redis.setex(history_key, 7200, json.dumps(trimmed, ensure_ascii=False))

          yield f"data: {json.dumps({'type': 'done'})}\n\n"

      return generate()

  ---
  3. app/api/routes/ai.py

  加 import 和新 endpoint：

  from fastapi.responses import StreamingResponse
  from app.schemas_DTO.ai import ChatRequest
  from app.services.ai_service import chat_ai

  @router.post("/chat")
  def chat(
      body: ChatRequest,
      payload: dict = Depends(get_current_token),
  ):
      """
      Streaming chat with CAG+RAG and conversation history
      """
      user_id = payload.get("sub")
      generator = chat_ai(
          user_id=user_id,
          message=body.message,
          conversation_id=body.conversation_id,
          destinations=body.destinations,
          use_web_search=body.use_web_search,
          show_thinking=body.show_thinking,
      )
      return StreamingResponse(generator, media_type="text/event-stream")

  ---
  測試方式（curl）

  curl -X POST http://localhost:8000/api/ai/chat \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"message": "幫我規劃大阪3天行程", "destinations": ["Osaka"]}' \
    --no-buffer












    推薦架構：SSE Streaming + conversation history

  前端對話框
      ↓ 送出訊息 + conversation_id
  後端 /ai/chat (SSE endpoint)
      ↓ 組出完整 messages history
      ↓ stream=True 呼叫 LLM
      ↓ 一邊生成一邊推送 token 到前端
  前端即時顯示文字（像 ChatGPT 那樣）
  conversation history 存在哪：

  ┌─────────────────────┬──────────────────────────┐
  │        選項         │         適合情境         │
  ├─────────────────────┼──────────────────────────┤
  │ Redis (TTL 1-2小時) │ 短暫對話，不需要永久保存 │
  ├─────────────────────┼──────────────────────────┤
  │ Supabase            │ 要讓 user 之後回來繼續看 │
  ├─────────────────────┼──────────────────────────┤
  │ 前端自己維護        │ 最簡單，refresh 就消失   │
  └─────────────────────┴──────────────────────────┘

  流程：
  前端送 message + conversation_id (第一次沒有)
      ↓
  Redis 取出該 conversation 的 history
      ↓
  CAG 注入 system prompt
  RAG 如果有 destinations 就觸發
      ↓
  LLM stream=True 一邊生成一邊推 token
      ↓
  Redis 存更新後的 history (TTL 2小時)
      ↓
  第一個 SSE event 帶 conversation_id，後續帶 token

  SSE 格式（前端接收）：
  data: {"type": "meta", "conversation_id": "abc-123"}
  data: {"type": "token", "content": "好的"}
  data: {"type": "token", "content": "，大阪"}
  data: {"type": "done"}