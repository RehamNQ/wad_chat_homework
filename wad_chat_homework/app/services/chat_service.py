from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import Chat
from app.models.message import Message
from app.models.user import User
from app.services.llm_service import LLMService


class ChatService:
    @staticmethod
    async def list_chats_for_user(db: AsyncSession, user: User) -> list[Chat]:
        result = await db.execute(
            select(Chat).where(Chat.user_id == user.id).order_by(desc(Chat.updated_at), desc(Chat.id))
        )
        return list(result.scalars().all())

    @staticmethod
    async def create_chat(db: AsyncSession, user: User, title: str = "New Chat") -> Chat:
        cleaned_title = title.strip() or "New Chat"
        chat = Chat(user_id=user.id, title=cleaned_title[:150])
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat

    @staticmethod
    async def get_user_chat_or_404(db: AsyncSession, user: User, chat_id: int) -> Chat:
        result = await db.execute(
            select(Chat)
            .options(selectinload(Chat.messages))
            .where(Chat.id == chat_id, Chat.user_id == user.id)
        )
        chat = result.scalar_one_or_none()
        if not chat:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found.")
        return chat

    @staticmethod
    async def get_chat_list_context(db: AsyncSession, user: User) -> dict[str, Any]:
        chats = await ChatService.list_chats_for_user(db, user)
        return {"chats": chats, "error": None}

    @staticmethod
    async def get_chat_detail_context(
        db: AsyncSession,
        user: User,
        chat_id: int,
        error: str | None = None,
        message_value: str = "",
    ) -> dict[str, Any]:
        chat = await ChatService.get_user_chat_or_404(db, user, chat_id)
        chats = await ChatService.list_chats_for_user(db, user)
        return {"chat": chat, "chats": chats, "error": error, "message_value": message_value}

    @staticmethod
    def _build_prompt(chat: Chat, new_message: str) -> str:
        previous_messages = chat.messages[-6:] if chat.messages else []
        lines = [
            "You are a helpful assistant inside a university web application homework project.",
            "Give short, clear, friendly answers unless the user asks for more detail.",
            "",
        ]
        for message in previous_messages:
            prefix = "User" if message.role == "user" else "Assistant"
            lines.append(f"{prefix}: {message.content}")
        lines.append(f"User: {new_message}")
        lines.append("Assistant:")
        return "\n".join(lines)

    @staticmethod
    async def send_message_and_generate_reply(
        db: AsyncSession,
        user: User,
        chat_id: int,
        content: str,
    ) -> tuple[Chat, Message, Message]:
        cleaned_content = content.strip()
        if not cleaned_content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message cannot be empty.")

        chat = await ChatService.get_user_chat_or_404(db, user, chat_id)

        user_message = Message(chat_id=chat.id, role="user", content=cleaned_content)
        db.add(user_message)
        await db.flush()

        if chat.title == "New Chat":
            chat.title = cleaned_content[:60]

        chat.updated_at = datetime.now(timezone.utc)

        prompt = ChatService._build_prompt(chat, cleaned_content)
        assistant_text = LLMService.generate_reply(prompt)
        assistant_message = Message(chat_id=chat.id, role="assistant", content=assistant_text)
        db.add(assistant_message)
        await db.commit()
        await db.refresh(chat)
        await db.refresh(user_message)
        await db.refresh(assistant_message)
        return chat, user_message, assistant_message

    @staticmethod
    async def send_message_api_response(
        db: AsyncSession,
        user: User,
        chat_id: int,
        content: str,
    ) -> list[Message]:
        _, user_message, assistant_message = await ChatService.send_message_and_generate_reply(
            db,
            user,
            chat_id,
            content,
        )
        return [user_message, assistant_message]

    @staticmethod
    async def submit_message_from_web(
        db: AsyncSession,
        user: User,
        chat_id: int,
        content: str,
    ) -> dict[str, Any]:
        try:
            await ChatService.send_message_and_generate_reply(db, user, chat_id, content)
            return {"redirect_url": f"/chats/{chat_id}", "context": None, "status_code": status.HTTP_303_SEE_OTHER}
        except HTTPException as exc:
            context = await ChatService.get_chat_detail_context(
                db,
                user,
                chat_id,
                error=str(exc.detail),
                message_value=content,
            )
            return {"redirect_url": None, "context": context, "status_code": exc.status_code}
