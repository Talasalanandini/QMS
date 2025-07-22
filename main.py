from fastapi import FastAPI
from api import employeemanagement
from startup import ensure_admin_user
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
from fastapi import APIRouter
import datetime
from api.profilemanagemet import router as profile_router
from api.auditmanagement import router as audit_router

load_dotenv()

ensure_admin_user()

app = FastAPI()

router = APIRouter(tags=["Employee Management"])

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="QMS",
        version="1.0.0",
        description="API for managing employees, roles, and departments.",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    for path, methods in openapi_schema["paths"].items():
        for method in methods.values():
            # Only require BearerAuth for /profile/change-password
            if path == "/profile/change-password":
                method["security"] = [{"BearerAuth": []}]
            elif path.startswith("/profile"):
                method["security"] = []
            elif not (path == "/login" and method.get("operationId", "").startswith("admin_login")):
                method["security"] = [{"BearerAuth": []}]
            else:
                method["security"] = []
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.include_router(employeemanagement.router)
app.include_router(profile_router)
app.include_router(audit_router)
