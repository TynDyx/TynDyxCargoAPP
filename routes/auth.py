import random

import pytesseract
from PIL import Image
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.auth_tokens import create_access_token, get_current_user
from core.logger import logger
from database import db
from database.db import checker_user

router = APIRouter()
templates = Jinja2Templates(directory="templates")
limiter = Limiter(key_func=get_remote_address)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


async def send_mock_sms(phone: str, otp_code: str):
    logger.info(f"SMS yuborilmoqda: Phone={phone}, Code={otp_code}")
    print("\n" + "!" * 40)
    print(f"SMS YUBORILDI!")
    print(f"KIMGA: {phone}")
    print(f"KOD: {otp_code}")
    print("!" * 40 + "\n")
    return True


@router.get("/login")
async def login_page(request: Request):
    user = get_current_user(request=request)
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
@limiter.limit("2/second")
async def register_post(request: Request, full_name: str = Form(...), phone: str = Form(...),
                        password: str = Form(...), role: str = Form(...)):
    request.session["temp_user"] = {
        "full_name": full_name,
        "phone": phone,
        "password": password,
        "role": role
    }
    logger.info(f"Yangi ro'yxatdan o'tish boshlandi: {phone} ({role})")

    if role == "driver":
        return RedirectResponse(url="/verify_dr", status_code=303)
    else:
        otp_code = str(random.randint(1000, 9999))
        request.session["otp_code"] = otp_code
        await send_mock_sms(phone, otp_code)
        return RedirectResponse(url="/verify_sms", status_code=303)


@router.get("/verify_dr")
async def verifying_driving_lc(request: Request):
    temp_user = request.session.get("temp_user")
    if not temp_user or temp_user.get("role") != "driver":
        logger.warning("Ruxsatsiz verify_dr sahifasiga kirish urinishi")
        return RedirectResponse(url="/register", status_code=302)

    attempts = request.session.get("verify_attempts", 0)
    return templates.TemplateResponse("verify_dr.html", {
        "request": request,
        "remaining": 3 - attempts,
        "error": request.query_params.get("error")
    })


@router.post("/verify-process")
async def verify_process(request: Request, license_photo: UploadFile = File(...)):
    temp_user = request.session.get("temp_user")
    if not temp_user:
        return RedirectResponse(url="/register", status_code=302)

    attempts = request.session.get("verify_attempts", 0)

    try:
        img = Image.open(license_photo.file)
        text = pytesseract.image_to_string(img).upper()
        keywords = ["HAYDOVCHILIK", "GUVOHNOMASI", "LICENSE", "CE", "DRIVING"]

        if any(word in text for word in keywords):
            logger.info(f"OCR muvaffaqiyatli: {temp_user['phone']} guvohnomasi tasdiqlandi")
            otp_code = str(random.randint(1000, 9999))
            request.session["otp_code"] = otp_code
            await send_mock_sms(otp_code=otp_code, phone=temp_user['phone'])
            return RedirectResponse(url="/verify_sms", status_code=303)
        else:
            attempts += 1
            request.session["verify_attempts"] = attempts
            logger.warning(f"OCR xatosi: {temp_user['phone']} uchun kalit so'zlar topilmadi. Urinish: {attempts}")

            if attempts >= 3:
                logger.error(f"Ro'yxatdan o'tish rad etildi: {temp_user['phone']} limitdan oshdi")
                request.session.clear()
                return RedirectResponse(url="/register", status_code=303)

            return RedirectResponse(url="/verify_dr?error=1", status_code=303)
    except Exception as e:
        logger.error(f"OCR jarayonida texnik xato: {str(e)}")
        return RedirectResponse(url="/verify_dr?error=tech", status_code=303)


@router.post("/verify-sms-process")
async def verify_sms_process(request: Request, otp: str = Form(...)):
    temp_user = request.session.get("temp_user")
    saved_otp = request.session.get("otp_code")

    if otp == saved_otp:
        db.create_user(temp_user['full_name'], temp_user['phone'], temp_user['password'], temp_user['role'])
        logger.info(f"Foydalanuvchi muvaffaqiyatli yaratildi: {temp_user['phone']}")
        request.session.clear()
        return RedirectResponse(url="/login", status_code=303)
    else:
        logger.warning(f"Noto'g'ri OTP kiritildi: {temp_user.get('phone') if temp_user else 'Unknown'}")
        return RedirectResponse(url="/verify_sms?error=1", status_code=303)


@router.post("/login")
@limiter.limit("5/second")
async def login_post(request: Request, phone: str = Form(...), password: str = Form(...)):
    user = db.get_user_by_phone(phone)
    if user and checker_user(phone=phone, psw=password):
        token = create_access_token({"user_id": user[0][0], "role": user[0][3]})
        logger.info(f"Login muvaffaqiyatli: {phone} (ID: {user[0][0]})")
        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(key="access_token", value=token)
        return response

    logger.warning(f"Login muvaffaqiyatsiz: {phone}")
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Login yoki parol noto'g'ri kiritilgan"
    })


@router.get("/logout")
async def logout(request: Request):
    user = get_current_user(request)
    if user:
        logger.info(f"Foydalanuvchi tizimdan chiqdi: ID {user['user_id']}")
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(key="access_token", path="/")
    return response
