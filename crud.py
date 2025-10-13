# backend/crud.py
from sqlalchemy.orm import Session
from datetime import datetime
from models import User, Transaction
from schemas import TransactionCreate

# Users
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password: str, role: str = "user"):
    from auth import hash_password
    u = User(username=username, password_hash=hash_password(password), role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def get_users(db: Session):
    return db.query(User).all()

# Transactions
def create_transaction(db: Session, user: User, tx_in: TransactionCreate) -> Transaction:
    tx = Transaction(user_id=user.id, category=tx_in.category, amount=tx_in.amount, date=tx_in.date, note=tx_in.note)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx

def list_transactions(db: Session):
    # returns list of Transaction objects with related user loaded
    return db.query(Transaction).order_by(Transaction.date.desc()).all()

def delete_transaction(db: Session, tx_id: int):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if tx:
        db.delete(tx)
        db.commit()
        return True
    return False
