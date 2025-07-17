from fastapi import FastAPI
from api import employeemanagement
from startup import ensure_admin_user
from dotenv import load_dotenv

load_dotenv()

ensure_admin_user()

app = FastAPI()

app.include_router(employeemanagement.router)
