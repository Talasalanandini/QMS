from fastapi import APIRouter, Depends, HTTPException
from schemas import ProfileUpdateSchema, PasswordChangeSchema, SignatureSchema
from api.employeemanagement import admin_auth
from db.database import SessionLocal
from passlib.hash import bcrypt
from models import Employee

router = APIRouter(prefix="/profile", tags=["Profile Management"])

# Profile management business logic stubs

def get_profile():
    """Fetch and return the profile (no username required)."""
    # TODO: Implement database fetch logic
    return {"message": "Profile fetched"}

def update_profile(profile_data):
    """Update the profile with the provided data (no username required)."""
    # TODO: Implement database update logic
    return {"message": "Profile updated"}

def change_password(password_data, current_user):
    session = SessionLocal()
    try:
        user = session.query(Employee).filter(Employee.id == current_user.id).first()
        if not user or not bcrypt.verify(password_data.old_password, str(user.password)):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if int(getattr(user, 'must_reset_password', 0)) != 1:
            raise HTTPException(status_code=403, detail="Password change not allowed. Please contact admin.")
        # Fix linter: assign to instance attributes, not Column objects
        setattr(user, 'password', bcrypt.hash(password_data.new_password))
        setattr(user, 'must_reset_password', 0)
        session.commit()
        return {"message": "Password changed successfully"}
    finally:
        session.close()

def save_signature(signature_data):
    """Save the e-signature (no username required)."""
    # TODO: Implement e-signature save logic with role check
    return {"message": "Signature saved"}

def upload_avatar(file, current_user):
    import os
    from db.database import SessionLocal
    uploads_dir = 'uploads'
    os.makedirs(uploads_dir, exist_ok=True)
    file_location = os.path.join(uploads_dir, file.filename)
    with open(file_location, "wb") as f:
        f.write(file.file.read())
    # Update the user's avatar_url in the database
    session = SessionLocal()
    try:
        user = session.query(Employee).filter(Employee.id == current_user.id).first()
        if user:
            user.avatar_url = file_location
            session.commit()
    finally:
        session.close()
    return {"message": "Avatar uploaded successfully", "file_path": file_location}



