from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import RedirectResponse
from database import db
from core.auth_tokens import get_current_user
from database.db import get_order_by_id, get_user_by_phone
from core.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)


@router.post("/send-feedback/{order_id}")
@limiter.limit("5/second")
async def send_feedback(order_id: int, request: Request, comment: str = Form(...)):
    user = get_current_user(request)
    if not user or user['role'] != "driver":
        logger.warning(f"Ruxsatsiz feedback urinishi: User {user.get('user_id') if user else 'Guest'}")
        return RedirectResponse(url="/login", status_code=302)

    try:
        user_ph = get_order_by_id(order_id=order_id)
        manager = get_user_by_phone(user_ph[3])
        manager_id = manager[0][0]

        db.create_order_offer(
            order_id=order_id,
            driver_id=user['user_id'],
            message=comment
        )
        db.create_notification(
            user_id=manager_id,
            message=f"Haydovchi {user['user_id']} buyurtmangizga taklif qoldirdi.",
            order_id=order_id,
            from_id=user['user_id'],
        )
        logger.info(f"Haydovchi {user['user_id']} order {order_id} ga taklif qoldirdi")
        return RedirectResponse(url="/dashboard?msg=sent", status_code=303)
    except Exception as e:
        logger.error(f"Feedback yuborishda xato (Order: {order_id}): {e}")
        return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/offer/{notif_id}")
@limiter.limit("2/second")
async def view_offer(request: Request, notif_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    db.mark_as_read(notif_id)
    data = db.get_full_notification_data(notif_id)
    if not data:
        logger.error(f"Notifikatsiya topilmadi: {notif_id}")
        return "Ma'lumot topilmadi"

    logger.info(f"User {user['user_id']} notif {notif_id} ni ko'rdi")
    return templates.TemplateResponse("order_offer.html", {
        "request": request,
        "order": data['order'],
        "driver": data['driver'],
        "offer": data['offer'],
        "notif_id": notif_id
    })


@router.post("/reject/{offer_id}")
async def reject(offer_id: int, notif_id: int):
    db.reject_driver_offer(offer_id)
    logger.info(f"Taklif rad etildi: Offer ID {offer_id}")
    return RedirectResponse(f"/offer/{notif_id}", status_code=303)


@router.post("/approve/{offer_id}")
@limiter.limit("5/second")
async def approve(request: Request, offer_id: int, notif_id: int):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)

    data = db.get_full_notification_data(notif_id)
    if data:
        db.approve_driver_offer(
            offer_id=offer_id,
            driver_id=data['driver'][0],
            order_id=data['order'][0],
            manager_id=user['user_id']
        )
        logger.info(f"Taklif tasdiqlandi: Offer {offer_id} (Manager: {user['user_id']})")

    return RedirectResponse(f"/offer/{notif_id}", status_code=303)