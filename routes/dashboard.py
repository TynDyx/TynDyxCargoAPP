from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.responses import RedirectResponse

from database import db
from core.auth_tokens import get_current_user
from core.logger import logger

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)


@router.get("/dashboard")
@limiter.limit("5/second")
async def dashboard_page(request: Request):
    user = get_current_user(request)

    if not user:
        logger.warning("Dashboardga ruxsatsiz kirish urinishi: Foydalanuvchi tizimga kirmagan")
        return RedirectResponse(url="/login", status_code=302)

    try:
        orders = db.get_all_orders()
        notifications = db.get_unread_notifications(user['user_id'])
        logger.info(
            f"Dashboard yuklandi: User ID {user['user_id']} | "
            f"Role: {user.get('role')} | "
            f"Orders count: {len(orders)} | "
            f"Unread notifs: {len(notifications)}"
        )

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "orders": orders,
            "notifications": notifications,
            "notif_count": len(notifications)
        })

    except Exception as e:
        logger.error(f"Dashboardni yuklashda xatolik yuz berdi (User ID {user['user_id']}): {str(e)}")
        return RedirectResponse(url="/profile?error=dashboard_failed")
