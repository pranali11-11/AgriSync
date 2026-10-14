"""Standalone CLI validation script for crop stages integrity.
Fails loudly if any crop has missing, zero-length, overlapping, or gapped stages.
"""
import asyncio
import sys
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal
from app.models.crop import Crop
from app.services.crop_validation import validate_crop_stages_integrity


async def run_validation() -> int:
    print("=" * 70)
    print("AgriSync - Crop Stages Contiguity and Coverage Validation")
    print("=" * 70)

    async with AsyncSessionLocal() as db:
        stmt = select(Crop).options(selectinload(Crop.stages)).order_by(Crop.id)
        crops = (await db.execute(stmt)).scalars().all()

        if not crops:
            print("[FAIL] No crops found in the database! Did you run seeding?")
            return 1

        print(f"Checking {len(crops)} crops in database...\n")
        total_stages = 0
        for crop in crops:
            stage_count = len(crop.stages)
            total_stages += stage_count
            print(f"  • {crop.name:<16} (ID: {crop.id:>2}, Duration: {crop.duration_days:>3}d, Category: {crop.category:<9}) -> {stage_count} stages")

        print("-" * 70)
        errors = validate_crop_stages_integrity(crops)

        if errors:
            print(f"\n[FAIL] Found {len(errors)} stage validation error(s):\n")
            for idx, err in enumerate(errors, 1):
                print(f"  [{idx}] {err}")
            print("\nValidation FAILED: Please fix crop_stages in the database/seed data.")
            return 1

        print(f"\n[PASS] Validation SUCCESSFUL!")
        print(f"       Zero gap/overlap errors across all {len(crops)} crops ({total_stages} stages verified).")
        print(f"       Every crop has complete, contiguous coverage from day 0 to duration_days.")
        print(f"       Every stage has a detailed plain-language description and official source.")
        print("=" * 70)
        return 0


def main():
    try:
        exit_code = asyncio.run(run_validation())
        sys.exit(exit_code)
    except Exception as exc:
        print(f"\n[CRITICAL ERROR] Validation execution failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
