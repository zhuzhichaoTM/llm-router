"""
Verify that priority and weight columns are accessible in provider_models.

This script verifies that the priority and weight columns were added correctly
and can be accessed through SQLAlchemy.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from src.db.base import async_session_maker
from src.models.provider import ProviderModel


async def verify():
    """Verify priority and weight columns."""
    print("Verifying priority and weight columns in provider_models...")
    print()

    # Check raw SQL first
    print("1. Checking raw SQL query:")
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT model_id, name, priority, weight FROM provider_models LIMIT 3")
        )
        rows = result.fetchall()
        for row in rows:
            print(f"  {row[0]}: priority={row[2]}, weight={row[3]}")

    print()

    # Check SQLAlchemy model
    print("2. Checking SQLAlchemy model query:")
    async with async_session_maker() as session:
        result = await session.execute(
            select(ProviderModel).limit(3)
        )
        models = result.scalars().all()
        for model in models:
            print(f"  {model.model_id}: priority={model.priority}, weight={model.weight}")

    print()

    # Check if columns exist in the model
    print("3. Checking model attributes:")
    model_attrs = dir(ProviderModel)
    print(f"  Has 'priority' attribute: {'priority' in model_attrs}")
    print(f"  Has 'weight' attribute: {'weight' in model_attrs}")

    print()
    print("✓ Verification complete!")


async def main():
    """Main function."""
    try:
        await verify()
    except Exception as e:
        print(f"\nERROR: Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
