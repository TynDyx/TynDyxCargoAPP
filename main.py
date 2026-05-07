from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from database import db
from core.config import SECRET_KEY
from routes import auth, orders, dashboard, profile, offers
from core.logger import logger

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")

db.init_db()
logger.info("Database muvaffaqiyatli ulandi")

app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(dashboard.router)
app.include_router(profile.router)
app.include_router(offers.router)


@app.get("/")
async def home():
    return RedirectResponse(url="/login")


logger.info("TynDyx dasturi to'liq ishga tushdi")
