"""Test that the modules import correctly"""
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./dep_health.db'
import sys
sys.path.insert(0, os.path.dirname(__file__))

print("Step 1: importing app.db.session...")
from app.db.session import Base, engine, async_session_maker, init_db
print("Step 2: importing app.db.models...")
from app.db.models import Project, Scan, HealthReport
print("Step 3: tables creation...")

import asyncio
async def create():
    async with engine.begin() as conn:
        from app.db import models
        await conn.run_sync(models.Base.metadata.create_all)
        print("Tables created OK")
    await engine.dispose()

asyncio.run(create())

print("\nStep 4: database file test...")
import sqlite3
conn = sqlite3.connect('dep_health.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tables in DB: {[t[0] for t in tables]}")
conn.close()
