#!/usr/bin/env python3
"""
Seed the database with commonly researched companies.
Run once after alembic upgrade head.

Usage:
    python infra/scripts/seed_companies.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.db.session import SessionLocal
from app.db.models import Company


SEED_COMPANIES = [
    # Indonesian banks
    {"name": "Bank Central Asia", "ticker": "BBCA", "country": "ID", "industry": "Consumer banking", "website": "https://www.bca.co.id"},
    {"name": "Bank Rakyat Indonesia", "ticker": "BBRI", "country": "ID", "industry": "Consumer banking", "website": "https://www.bri.co.id"},
    {"name": "Bank Mandiri", "ticker": "BMRI", "country": "ID", "industry": "Commercial banking", "website": "https://www.bankmandiri.co.id"},
    {"name": "Bank Negara Indonesia", "ticker": "BBNI", "country": "ID", "industry": "Commercial banking", "website": "https://www.bni.co.id"},

    # Indonesian tech
    {"name": "GoTo", "ticker": "GOTO", "country": "ID", "industry": "Super-app / e-commerce", "website": "https://www.goto.co.id"},
    {"name": "Bukalapak", "ticker": "BUKA", "country": "ID", "industry": "E-commerce", "website": "https://www.bukalapak.com"},

    # Indonesian telco and conglomerate
    {"name": "Telkom Indonesia", "ticker": "TLKM", "country": "ID", "industry": "Telecommunications", "website": "https://www.telkom.co.id"},
    {"name": "Astra International", "ticker": "ASII", "country": "ID", "industry": "Diversified conglomerate", "website": "https://www.astra.co.id"},

    # Southeast Asia regional
    {"name": "Sea Limited", "ticker": "SE", "country": "SG", "industry": "Digital entertainment / e-commerce / fintech", "website": "https://www.sea.com"},
    {"name": "Grab", "ticker": "GRAB", "country": "SG", "industry": "Super-app / mobility / fintech", "website": "https://www.grab.com"},
    {"name": "Singtel", "ticker": "Z74", "country": "SG", "industry": "Telecommunications", "website": "https://www.singtel.com"},

    # Global benchmarks
    {"name": "Stripe", "ticker": None, "country": "US", "industry": "Payments infrastructure", "website": "https://stripe.com"},
    {"name": "Adyen", "ticker": "ADYEN", "country": "NL", "industry": "Payments infrastructure", "website": "https://www.adyen.com"},
]


async def seed():
    async with SessionLocal() as session:
        added = 0
        for data in SEED_COMPANIES:
            existing = await session.execute(
                __import__("sqlalchemy").select(Company).where(Company.name == data["name"])
            )
            if existing.scalar_one_or_none():
                print(f"  skip (exists): {data['name']}")
                continue

            company = Company(**data)
            session.add(company)
            added += 1
            print(f"  added: {data['name']}")

        await session.commit()
        print(f"\nDone. Added {added} companies.")


if __name__ == "__main__":
    asyncio.run(seed())
