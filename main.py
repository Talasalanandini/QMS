from fastapi import FastAPI
from api import employeemanagement
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi
from fastapi import APIRouter
import datetime
from api.profilemanagemet import router as profile_router
from api.auditmanagement import router as audit_router
from api.companymanagement import router as company_router
from api.documentmanagement import router as document_router
from api.trainingmanagement import router as training_router
from api.usermanagement import router as user_router
from api.projectmanagement import router as project_router

load_dotenv()

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
            elif not (path == "/login" and method.get("operationId", "").startswith("user_login")):
                method["security"] = [{"BearerAuth": []}]
            else:
                method["security"] = []
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.include_router(employeemanagement.router)
app.include_router(user_router)
app.include_router(profile_router)
app.include_router(audit_router)
app.include_router(company_router)
app.include_router(document_router)
app.include_router(training_router)
app.include_router(project_router)
