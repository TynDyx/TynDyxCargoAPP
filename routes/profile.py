import os
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database import db
from core.auth_tokens import get_current_user
from database.db import get_user_by_id, get_user_by_phone, get_orders_by_owner
from core.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/profile")
async def profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        logger.warning("Avtorizatsiyadan o'tmagan foydalanuvchi profilga kirmoqchi bo'ldi")
        return RedirectResponse("/login")

    try:
        user_if = get_user_by_id(user_id=int(user["user_id"]))
        user_info = get_user_by_phone(phone=user_if[0][0])

        logger.info(f"Foydalanuvchi profiliga kirdi: ID {user['user_id']} ({user_info[0][3]})")

        if user_info[0][3] == 'manager':
            user_orders = get_orders_by_owner(user_if[0][0])
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user": user_info[0],
                "orders": user_orders
            })
        elif user_info[0][3] == 'driver':
            user_offers = db.get_driver_offers(user['user_id'])
            return templates.TemplateResponse("profile.html", {
                "request": request,
                "user": user_info[0],
                "offers": user_offers
            })

    except Exception as e:
        logger.error(f"Profil yuklashda xatolik (User: {user.get('user_id')}): {e}")
        return RedirectResponse("/dashboard")


@router.get("/profile/update")
async def update_get_profile_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    user_phone = get_user_by_id(user['user_id'])
    user_info = get_user_by_phone(user_phone[0][0])

    logger.info(f"Profil tahrirlash sahifasiga kirildi: ID {user['user_id']}")
    return templates.TemplateResponse("update_pr.html", {"request": request, "user": user_info[0]})


@router.post("/profile/update")
async def update_profile_page(request: Request, full_name: str = Form(None), desc: str = Form(None),
                              photo: UploadFile = File(None)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    user_phone = get_user_by_id(user['user_id'])
    user_info = get_user_by_phone(user_phone[0][0])
    if full_name is None or full_name.strip() == "":
        full_name = user_info[0][1]

    vuln_makers = {"webp", "jpeg", "png", "jpg"}
    photo_path2 = user_info[0][5]

    if photo and photo.filename:
        photo_check = photo.filename.split(".")[-1].lower()
        if photo_check not in vuln_makers:
            logger.warning(f"Noto'g'ri fayl formati yuklandi: {photo_check} (User: {user['user_id']})")
            return RedirectResponse("/profile/update", status_code=303)

        os.makedirs("static/uploads", exist_ok=True)
        file_path = f"static/uploads/{user['user_id']}_{photo.filename}"

        try:
            content = await photo.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            photo_path2 = f"/{file_path}"
            logger.info(f"Yangi profil rasmi yuklandi: {file_path}")
        except Exception as e:
            logger.error(f"Rasm yuklashda texnik xato: {e}")
        finally:
            await photo.close()

    try:
        db.update_pr(user_ids=user['user_id'], photo=photo_path2, desc=desc, full_name=full_name)
        logger.info(f"Profil muvaffaqiyatli yangilandi: ID {user['user_id']}")
    except Exception as e:
        logger.error(f"DB update xatosi (Profile): {e}")

    return RedirectResponse("/profile", status_code=303)


@router.get("/profile/{order_id}")
async def profile_order_detail(order_id: int, request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        order = db.get_order_by_id(order_id=order_id)
        offers = db.get_offers_by_order(order_id=order_id)

        logger.info(f"Buyurtma tafsilotlari ko'rildi: Order {order_id} (User: {user['user_id']})")

        return templates.TemplateResponse("profile_ord.html", {
            "request": request,
            "user": user,
            "order": order,
            "offers": offers
        })
    except Exception as e:
        logger.error(f"Buyurtma tafsilotlarini yuklashda xato (ID: {order_id}): {e}")
        return RedirectResponse(url="/profile", status_code=301)
