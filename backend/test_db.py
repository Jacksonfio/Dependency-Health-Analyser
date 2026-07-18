"""Quick test to verify database setup"""
import asyncio
import os
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///./dep_health.db'
import sys
sys.path.insert(0, os.path.dirname(__file__))

async def test():
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine('sqlite+aiosqlite:///./dep_health.db')
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print('Tables:', tables)
    await engine.dispose()

    from app.db.session import get_db, async_session_maker
    from app.api.v1.endpoints.projects import list_projects

    async with async_session_maker() as session:
        try:
            from fastapi import Depends
            print('Session created OK')
        except Exception as e:
            print('Session error:', e)

asyncio.run(test())
