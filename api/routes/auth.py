from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Annotated
from bson.objectid import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.models.user import UserCreate, UserLogin, GoogleLogin, UserResponse
from app.database import db, get_db
from app.utils.jwt import (
    verify_password, get_password_hash, create_access_token,
    verify_google_token, SECRET_KEY, ALGORITHM
)
from app.schemas.user import user_schema, user_response_schema

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = await db["users"].find_one({"_id": ObjectId(user_id)})
    if user is None:
        raise credentials_exception
        
    return user

@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    # Check if user already exists
    if await db["users"].find_one({"email": user_data.email}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user_dict = {
        "email": user_data.email,
        "password": hashed_password,
        "name": user_data.name,
        "created_at": datetime.utcnow()
    }
    
    result = await db["users"].insert_one(user_dict)
    
    # Get created user
    created_user = await db["users"].find_one({"_id": result.inserted_id})
    
    return user_response_schema(created_user)

@router.post("/login")
async def login_json(
    user_data: UserLogin,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    user = await db["users"].find_one({"email": user_data.email})
    
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user": user_response_schema(user)}

@router.post("/google")
async def google_login(
    google_data: GoogleLogin,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    token_info = verify_google_token(google_data.token)
    
    # Get user info from Google token
    email = token_info.get("email")
    name = token_info.get("name")
    
    # Check if user exists
    user = await db["users"].find_one({"email": email})
    
    if not user:
        # Create new user
        user_dict = {
            "email": email,
            "name": name,
            "password": get_password_hash("google_oauth_no_password"),  # placeholder password
            "created_at": datetime.utcnow()
        }
        result = await db["users"].insert_one(user_dict)
        user = await db["users"].find_one({"_id": result.inserted_id})
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": str(user["_id"])},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    return user_response_schema(current_user)

@router.post("/logout")
async def logout():
    # JWT is stateless, so actual logout happens on the client
    # This endpoint is provided for API completeness
    return {"message": "Logged out successfully"}

class ProfileUpdate(BaseModel):
    name: str = None
    profile_image: str = None

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Update user profile"""
    # Only allow updating certain fields
    update_data = {}
    if profile_data.name is not None:
        update_data["name"] = profile_data.name
    if profile_data.profile_image is not None:
        update_data["profile_image"] = profile_data.profile_image
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    # Update user in database
    result = await db["users"].update_one(
        {"_id": current_user["_id"]},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile update failed"
        )
    
    # Get updated user
    updated_user = await db["users"].find_one({"_id": current_user["_id"]})
    
    return user_response_schema(updated_user)