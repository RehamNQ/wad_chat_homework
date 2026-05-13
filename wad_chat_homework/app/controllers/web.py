from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, get_optional_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.chat_service import ChatService
from app.templates import render_template


router = APIRouter(tags=["web"])


@router.get("/")
async def home_page(request: Request, user: User | None = Depends(get_optional_current_user)):
    if user:
        return RedirectResponse(url="/chats", status_code=status.HTTP_303_SEE_OTHER)
    return render_template(request, "index.html", {}, user)


@router.get("/chats")
async def chat_list_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context = await ChatService.get_chat_list_context(db, current_user)
    return render_template(request, "chats/list.html", context, current_user)


@router.post("/chats")
async def create_chat_submit(
    title: str = Form(default="New Chat"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat = await ChatService.create_chat(db, current_user, title)
    return RedirectResponse(url=f"/chats/{chat.id}", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/chats/{chat_id}")
async def chat_detail_page(
    request: Request,
    chat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    context = await ChatService.get_chat_detail_context(db, current_user, chat_id)
    return render_template(request, "chats/detail.html", context, current_user)


@router.post("/chats/{chat_id}/messages")
async def send_message_submit(
    request: Request,
    chat_id: int,
    content: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await ChatService.submit_message_from_web(db, current_user, chat_id, content)
    if result["redirect_url"]:
        return RedirectResponse(url=result["redirect_url"], status_code=result["status_code"])
    return render_template(
        request,
        "chats/detail.html",
        result["context"],
        current_user,
        status_code=result["status_code"],
    )
