"""声纹库 API：CRUD + 录入 + 核验。"""

from __future__ import annotations

from typing import Annotated

from fastapi import Form, UploadFile
from pydantic import BaseModel, Field

from app.api.response import fail, ok
from app.services.voice import voiceprint_service as svc


class VoiceprintCreateBody(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=64)
    description: str = Field(default="", max_length=200)


class VoiceprintUpdateBody(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    description: str | None = Field(default=None, max_length=200)


async def list_voiceprints():
    return ok({"items": svc.list_voiceprints()})


async def create_voiceprint(body: VoiceprintCreateBody):
    try:
        item = svc.create_voiceprint(
            display_name=body.display_name,
            description=body.description,
        )
    except svc.VoiceprintError as exc:
        return fail(40041, "参数错误", str(exc))
    return ok(item)


async def update_voiceprint(profile_id: str, body: VoiceprintUpdateBody):
    try:
        item = svc.update_voiceprint(
            profile_id,
            display_name=body.display_name,
            description=body.description,
        )
    except svc.VoiceprintError as exc:
        return fail(40441, "不存在", str(exc))
    return ok(item)


async def delete_voiceprint(profile_id: str):
    try:
        svc.delete_voiceprint(profile_id)
    except svc.VoiceprintError as exc:
        return fail(40441, "不存在", str(exc))
    return ok({"deleted": True, "id": profile_id})


async def enroll_voiceprint(
    profile_id: str,
    file: UploadFile,
    sample_rate: Annotated[int | None, Form()] = 16000,
):
    if not file:
        return fail(40042, "参数错误", "未上传音频")
    try:
        audio = await file.read()
    except Exception as exc:  # noqa: BLE001
        return fail(40042, "参数错误", f"读取音频失败: {exc}")
    if not audio:
        return fail(40042, "参数错误", "音频为空")
    try:
        item = svc.enroll_voiceprint(
            profile_id,
            audio,
            sample_rate=sample_rate or 16000,
        )
    except svc.VoiceprintError as exc:
        return fail(40043, "录入失败", str(exc))
    return ok(item)


async def verify_voiceprint(
    profile_id: Annotated[str, Form()],
    file: UploadFile,
    sample_rate: Annotated[int | None, Form()] = 16000,
):
    if not profile_id.strip():
        return fail(40044, "参数错误", "未选择声纹用户")
    if not file:
        return fail(40044, "参数错误", "未上传音频")
    try:
        audio = await file.read()
    except Exception as exc:  # noqa: BLE001
        return fail(40044, "参数错误", f"读取音频失败: {exc}")
    if not audio:
        return fail(40044, "参数错误", "音频为空")
    try:
        result = svc.verify_voiceprint(
            profile_id.strip(),
            audio,
            sample_rate=sample_rate or 16000,
        )
    except svc.VoiceprintError as exc:
        return fail(40045, "核验失败", str(exc))
    if not result.get("matched"):
        return ok(result, message="声纹不匹配")
    return ok(result)
