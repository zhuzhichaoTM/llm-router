"""
Add priority and weight columns to provider_models table.

This script adds the priority and weight columns to existing provider_models tables.
Run this script after updating the code to enable model-level priority and weight.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.db.base import engine


async def migrate():
    """Add priority and weight columns to provider_models table."""
    print("Adding priority and weight columns to provider_models table...")

    async with engine.begin() as conn:
        # Check if columns already exist
        result = await conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'provider_models' AND column_name IN ('priority', 'weight')
        """))
        existing_columns = {row[0] for row in result}

        # Add priority column if it doesn't exist
        if 'priority' not in existing_columns:
            print("  Adding priority column...")
            await conn.execute(text("""
                ALTER TABLE provider_models
                ADD COLUMN priority INTEGER NOT NULL DEFAULT 100
            """))
            print("  ✓ Priority column added")
        else:
            print("  - Priority column already exists")

        # Add weight column if it doesn't exist
        if 'weight' not in existing_columns:
            print("  Adding weight column...")
            await conn.execute(text("""
                ALTER TABLE provider_models
                ADD COLUMN weight INTEGER NOT NULL DEFAULT 100
            """))
            print("  ✓ Weight column added")
        else:
            print("  - Weight column already exists")

    print("\nMigration completed successfully!")
    print("\nModel priority and weight are now configured per-model instead of per-provider.")
    print("\nNext steps:")
    print("1. Restart the application")
    print("2. Configure priority and weight for individual models in the Routing page")


async def main():
    """Main migration function."""
    try:
        await migrate()
    except Exception as e:
        print(f"\nERROR: Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
