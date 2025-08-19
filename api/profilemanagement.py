from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from services.profileservice import get_profile, update_profile, change_password, save_signature, upload_avatar
from schemas import ProfileUpdateSchema, PasswordChangeSchema, SignatureSchema, FirstPasswordResetSchema
from db.database import SessionLocal
from models import Employee, Token
from passlib.hash import bcrypt
from services import profileservice

router = APIRouter(prefix="/profile", tags=["Profile Management"])

def get_current_user(request: Request):
    session = SessionLocal()
    try:
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        access_token = authorization.split(" ", 1)[1]
        token_obj = session.query(Token).filter(Token.token == access_token, Token.revoked == 0).first()
        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")
        user = session.query(Employee).filter(Employee.id == token_obj.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    finally:
        session.close()

@router.get("")
def read_profile():
    return get_profile()

@router.put("")
def edit_profile(profile_data: ProfileUpdateSchema):
    return update_profile(profile_data)

@router.post("/change-password")
def change_user_password(password_data: PasswordChangeSchema, current_user: Employee = Depends(get_current_user)):
    if int(getattr(current_user, 'must_reset_password', 0)) != 1:
        raise HTTPException(status_code=403, detail="Password change not allowed. Please contact admin.")
    return profileservice.change_password(password_data, current_user)

@router.post("/e-signature")
def save_e_signature(signature_data: SignatureSchema):
    return save_signature(signature_data)

@router.post("/upload-avatar")
def upload_avatar_api(file: UploadFile = File(...)):
    # Remove current_user dependency, call upload_avatar with only file
    return upload_avatar(file, None)

@router.post("/first-reset-password")
def first_reset_password(data: FirstPasswordResetSchema):
    session = SessionLocal()
    try:
        user = session.query(Employee).filter(Employee.email == data.email).first()
        if user is not None:
            user: Employee = user  # type: ignore
        if not user or not bcrypt.verify(data.old_password, str(user.password)):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user or int(getattr(user, 'must_reset_password', 0)) != 1:
            raise HTTPException(status_code=403, detail="Password reset not allowed")
        user.password = bcrypt.hash(data.new_password)  # type: ignore
        user.must_reset_password = 0  # type: ignore
        session.commit()
        return {"message": "Password reset successful"}
    finally:
        session.close()
