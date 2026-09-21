"""Seed the database with sample products for local development/demo.

Run with: python -m app.seed
"""

from sqlmodel import Session, select

from app.db import engine, init_db
from app.models import Product

SAMPLE_PRODUCTS = [
    {
        "name": "Wireless Mouse",
        "description": "Ergonomic wireless mouse with USB-C charging.",
        "price": 24.99,
        "stock": 50,
        "image_url": "https://placehold.co/400x300?text=Wireless+Mouse",
    },
    {
        "name": "Mechanical Keyboard",
        "description": "Compact 75% mechanical keyboard with hot-swappable switches.",
        "price": 89.00,
        "stock": 30,
        "image_url": "https://placehold.co/400x300?text=Mechanical+Keyboard",
    },
    {
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI, SD card, and 100W passthrough.",
        "price": 39.50,
        "stock": 75,
        "image_url": "https://placehold.co/400x300?text=USB-C+Hub",
    },
    {
        "name": "27-inch 4K Monitor",
        "description": "27-inch 4K IPS monitor with USB-C and 60Hz refresh rate.",
        "price": 329.99,
        "stock": 15,
        "image_url": "https://placehold.co/400x300?text=4K+Monitor",
    },
    {
        "name": "Laptop Stand",
        "description": "Aluminum adjustable laptop stand, foldable for travel.",
        "price": 29.00,
        "stock": 0,
        "image_url": "https://placehold.co/400x300?text=Laptop+Stand",
    },
]


def seed() -> None:
    init_db()
    with Session(engine) as session:
        existing = session.exec(select(Product)).first()
        if existing:
            print("Products already exist, skipping seed.")
            return

        for data in SAMPLE_PRODUCTS:
            session.add(Product(**data))
        session.commit()
        print(f"Seeded {len(SAMPLE_PRODUCTS)} products.")


if __name__ == "__main__":
    seed()
