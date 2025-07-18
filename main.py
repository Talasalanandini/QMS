from fastapi import FastAPI
from api import employeemanagement
from startup import ensure_admin_user
from dotenv import load_dotenv
from fastapi.openapi.utils import get_openapi

load_dotenv()

ensure_admin_user()

app = FastAPI()

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="QMS API",
        version="1.0.0",
        description="QMS API with Bearer Auth",
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
            # Only require BearerAuth if not /login
            if not (path == "/login" and method.get("operationId", "").startswith("admin_login")):
                method["security"] = [{"BearerAuth": []}]
            else:
                method["security"] = []
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

app.include_router(employeemanagement.router)
