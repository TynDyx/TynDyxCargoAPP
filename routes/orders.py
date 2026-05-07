from typing import Optional
from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import RedirectResponse

from database import db
from core.auth_tokens import get_current_user
from database.db import get_order_by_id, get_user_by_id
from core.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)


@router.get("/order/{order_id}")
async def order_detail(order_id: str, request: Request):
    user = get_current_user(request)
    if not user:
        logger.warning(f"Ruxsatsiz buyurtmani ko'rish urinishi: Order ID {order_id}")
        return RedirectResponse(url="/login", status_code=302)

    try:
        order = get_order_by_id(order_id=int(order_id))
        logger.info(f"Buyurtma ko'rildi: User ID {user['user_id']} | Order ID {order_id}")
        return templates.TemplateResponse("view_order.html", {"request": request, "user": user, "order": order})
    except ValueError as e:
        logger.error(f"Buyurtma ID xatosi: {order_id} | {str(e)}")
        return RedirectResponse(url="/dashboard")


@router.get("/create-order")
async def create_order_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if user['role'] == "driver":
        logger.warning(f"Haydovchi buyurtma yaratish sahifasiga kirdi (Ruxsat yo'q): User ID {user['user_id']}")
        return RedirectResponse("/dashboard", status_code=302)

    return templates.TemplateResponse("create_order.html", {"request": request})


@router.post("/create-order")
async def create_order(
        request: Request,
        description: str = Form(...),
        order_type: str = Form(...),
        start_time: Optional[str] = Form(None),
        end_time: Optional[str] = Form(None)
):
    user = get_current_user(request)
    if not user or user['role'] == "driver":
        logger.error(f"Noqonuniy buyurtma yaratish urinishi: User ID {user.get('user_id') if user else 'Nomalum'}")
        return RedirectResponse("/dashboard", status_code=302)

    price = 10000 if order_type == "timed" else 5000

    request.session["pending_order"] = {
        "description": description,
        "order_type": order_type,
        "start_time": start_time,
        "end_time": end_time,
        "price": price
    }

    logger.info(f"Buyurtma kutilmoqda (Pending): User {user['user_id']} | Type: {order_type} | Price: {price}")
    return RedirectResponse(url="/checkout", status_code=303)


@router.get("/checkout")
async def checkout_page(request: Request):
    user = get_current_user(request)
    if not user or user['role'] == 'driver':
        return RedirectResponse("/dashboard", status_code=302)

    order = request.session.get("pending_order")
    if not order:
        logger.warning(f"Sessiyada buyurtma topilmadi: User ID {user['user_id']}")
        return RedirectResponse("/create-order")

    return templates.TemplateResponse("payment.html", {"request": request, "order": order})


@router.post("/confirm-payment")
async def confirm_payment(request: Request):
    order = request.session.get("pending_order")
    user = get_current_user(request)

    if not order or not user:
        logger.error("To'lovni tasdiqlashda sessiya ma'lumotlari yetishmadi")
        return RedirectResponse("/create-order")

    try:
        ph = get_user_by_id(user_id=user['user_id'])
        db.create_order(
            description=order['description'],
            phone=ph[0][0]
        )
        request.session.pop("pending_order")

        logger.info(f"To'lov muvaffaqiyatli: User {user['user_id']} yangi buyurtma yaratdi")
        return RedirectResponse("/dashboard?msg=To'lov muvaffaqiyatli yakunlandi", status_code=303)
    except Exception as e:
        logger.error(f"Buyurtmani DB ga saqlashda xato: {str(e)}")
        return RedirectResponse("/create-order?error=db_error")


@router.post("/delete-order/{order_id}")
@limiter.limit("3/second")
async def delete_order(request: Request, order_id):
    user = get_current_user(request)
    if not user or user['role'] == 'driver':
        logger.warning(f"Ruxsatsiz o'chirish urinishi: User {user.get('user_id')} | Order {order_id}")
        return RedirectResponse("/dashboard", status_code=303)

    try:
        user_ph = get_user_by_id(user_id=user['user_id'])
        deleting_order = db.inactivate_order(order_id=order_id, manager_phone=user_ph[0])
        if deleting_order is True:
            logger.info(f"Buyurtma o'chirildi (Inaktiv): Order ID {order_id} | Manager ID {user['user_id']}")
            return RedirectResponse("/profile", status_code=303)
        else:
            logger.warning(f"Buyurtma o'chirilmadi (Topilmadi yoki allaqachon inaktiv): Order ID {order_id}")
            return RedirectResponse("/profile", status_code=302)
    except Exception as e:
        logger.error(f"Buyurtmani o'chirishda texnik xato: Order {order_id} | {str(e)}")
        return RedirectResponse("/profile", status_code=302)
