# backend/schemas.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    username: str
    password: str

class TransactionCreate(BaseModel):
    category: str
    amount: float
    date: datetime
    note: Optional[str] = None

class TransactionOut(TransactionCreate):
    id: int
    user_id: int

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"

class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        orm_mode = True
