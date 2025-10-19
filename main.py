# backend/main.py
from fastapi import FastAPI, Depends, HTTPException, Response, Cookie, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import io
import csv
import os

from database import SessionLocal, init_db, get_db_engine
from models import User, Transaction
from schemas import LoginRequest, TransactionCreate, TransactionOut, UserCreate, UserOut
from auth import hash_password, verify_password, create_access_token, verify_token
from crud import (
    get_user_by_username, create_user, get_users,
    create_transaction, list_transactions, delete_transaction
)
from utils import record_log

# Initialize DB (creates tables if not exist)
init_db()

app = FastAPI(title="家計簿アプリ API")

# CORS origins (set FRONTEND_ORIGIN in .env or default)
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency: DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth dependency to get current user from HTTP-only cookie
def get_current_user(token: str = Cookie(None), db: Session = Depends(get_db)) -> User:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = verify_token(token)
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# --- startup: ensure initial users ---
@app.on_event("startup")
def create_initial_users():
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(username="alice", password_hash=hash_password("alice_pass"), role="admin")
            user = User(username="bob", password_hash=hash_password("bob_pass"), role="user")
            db.add_all([admin, user])
            db.commit()
    finally:
        db.close()

# --- Auth endpoints ---
@app.post("/api/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = get_user_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token({"sub": str(user.id)})
    # Set HTTP-only cookie
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=int(os.getenv("ACCESS_TOKEN_EXPIRE_SECONDS", "3600")),  # 1 hour default
        samesite="lax",
        secure=False if os.getenv("ENV", "dev") == "dev" else True
    )
    record_log(db, user.id, "LOGIN")
    return {"username": user.username, "role": user.role}

@app.post("/api/logout")
def logout(response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    response.delete_cookie("token")
    record_log(db, user.id, "LOGOUT")
    return {"message": "logged out"}

# --- Transactions ---
@app.post("/api/transactions", response_model=TransactionOut)
def api_create_transaction(payload: TransactionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = create_transaction(db=db, user=user, tx_in=payload)
    record_log(db, user.id, f"ADD_TX id={tx.id} type={payload.type}")
    return tx

@app.get("/api/transactions", response_model=List[TransactionOut])
def api_list_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # フィルタリング: 管理者は全ユーザーの取引を表示、一般ユーザーは自分の取引のみ
    if user.role == "admin":
        txs = db.query(Transaction).order_by(Transaction.date.desc()).all()
    else:
        txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.date.desc()).all()
    return txs

@app.delete("/api/transactions/{tx_id}")
def api_delete_transaction(tx_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    if user.role != "admin" and tx.user_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    delete_transaction(db=db, tx_id=tx_id)
    record_log(db, user.id, f"DELETE_TX id={tx_id}")
    return {"message": "deleted"}

# --- CSV export ---
@app.get("/api/transactions/csv")
def api_export_csv(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # フィルタリング: 管理者は全ユーザーの取引を表示、一般ユーザーは自分の取引のみ
    if user.role == "admin":
        txs = db.query(Transaction).order_by(Transaction.date.desc()).all()
    else:
        txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.date.desc()).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    # ヘッダー行に「種別」を追加
    writer.writerow(["id", "user_id", "username", "date", "category", "amount", "note", "type"])
    
    for t in txs:
        # typeを日本語に変換（収入/支出）
        type_jp = "収入" if getattr(t, 'type', 'expense') == "income" else "支出"
        writer.writerow([
            t.id, 
            t.user_id, 
            t.user.username if hasattr(t, "user") and t.user else "", 
            t.date.isoformat(), 
            t.category, 
            t.amount, 
            t.note or "",
            type_jp
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]), 
        media_type="text/csv", 
        headers={"Content-Disposition": "attachment; filename=transactions.csv"}
    )

# --- User management (admin only) ---
@app.get("/api/users", response_model=List[UserOut])
def api_list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return get_users(db=db)

@app.post("/api/users", response_model=UserOut)
def api_create_user(payload: UserCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    new = create_user(db=db, username=payload.username, password=payload.password, role=payload.role)
    record_log(db, user.id, f"CREATE_USER {new.username}")
    return new
