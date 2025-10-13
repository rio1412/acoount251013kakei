# backend/utils.py
from sqlalchemy.orm import Session
from models import Base, User
from datetime import datetime
import os
import csv

# Simple log recording into file and optionally DB logs table (DB logs table not implemented here)
def record_log(db: Session, user_id: int, action: str):
    logs_dir = os.getenv("LOG_DIR", "./logs")
    os.makedirs(logs_dir, exist_ok=True)
    ts = datetime.utcnow().isoformat()
    filename = os.path.join(logs_dir, "actions.log")
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"{ts}\tuser_id={user_id}\t{action}\n")
