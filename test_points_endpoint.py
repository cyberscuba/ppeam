#!/usr/bin/env python3
"""
Test script to diagnose the /api/points endpoint issue
"""
import asyncio
import sys
import os
from datetime import date

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

async def test_points_endpoint():
    """Test the points endpoint locally"""
    from app.database import AsyncSessionLocal, engine
    from app.models import Exhibitor, ExhibitorLeader, Admin, User, Hermano
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        # Test 1: Count exhibitors
        print("\n=== TEST 1: Count Exhibitors ===")
        result = await session.execute(select(Exhibitor))
        exhibitors = result.scalars().all()
        print(f"✅ Found {len(exhibitors)} exhibitors")

        if not exhibitors:
            print("⚠️  No exhibitors in database")
            return

        # Test 2: Check first exhibitor's leaders
        first_exhibitor = exhibitors[0]
        print(f"\n=== TEST 2: Leaders for '{first_exhibitor.name}' ===")

        try:
            # This is the problematic query
            leaders_result = await session.execute(
                select(ExhibitorLeader, Admin, User, Hermano)
                .join(Admin, ExhibitorLeader.admin_id == Admin.id)
                .outerjoin(User, Admin.user_id == User.id)
                .outerjoin(Hermano, Admin.hermano_id == Hermano.id)
                .where(ExhibitorLeader.exhibitor_id == first_exhibitor.id)
                .order_by(ExhibitorLeader.position)
            )
            leaders_data = leaders_result.all()
            print(f"✅ Query succeeded, found {len(leaders_data)} leaders")

            for leader, admin_obj, user_obj, hermano_obj in leaders_data:
                print(f"  - Admin: {admin_obj.username}, User: {user_obj.full_name if user_obj else 'N/A'}, Hermano: {hermano_obj.nombre if hermano_obj else 'N/A'}")

        except Exception as e:
            print(f"❌ ERROR in leader query: {e}")
            import traceback
            traceback.print_exc()

        # Test 3: Direct leader count
        print(f"\n=== TEST 3: Direct Leader Count ===")
        try:
            leader_count_result = await session.execute(
                select(ExhibitorLeader).where(ExhibitorLeader.exhibitor_id == first_exhibitor.id)
            )
            leader_count = len(leader_count_result.scalars().all())
            print(f"✅ Found {leader_count} leader records")
        except Exception as e:
            print(f"❌ ERROR: {e}")

        # Test 4: Check for broken admin records
        print(f"\n=== TEST 4: Check for Broken Admin Records ===")
        try:
            broken_admins_result = await session.execute(
                select(Admin).where(
                    (Admin.user_id == None) & (Admin.hermano_id == None)
                )
            )
            broken_admins = broken_admins_result.scalars().all()
            print(f"⚠️  Found {len(broken_admins)} admin records with no user_id AND no hermano_id")
            if broken_admins:
                for admin in broken_admins:
                    print(f"  - {admin.username} (id: {admin.id})")
        except Exception as e:
            print(f"❌ ERROR: {e}")

        # Test 5: Check for admin records referenced by leaders
        print(f"\n=== TEST 5: Check Admin Records Referenced by Leaders ===")
        try:
            leader_admins_result = await session.execute(
                select(Admin).join(ExhibitorLeader, Admin.id == ExhibitorLeader.admin_id)
            )
            leader_admins = leader_admins_result.scalars().all()
            print(f"✅ Found {len(leader_admins)} admin records referenced by leaders")

            broken_leader_admins = [a for a in leader_admins if a.user_id is None and a.hermano_id is None]
            if broken_leader_admins:
                print(f"⚠️  {len(broken_leader_admins)} of these have no user_id AND no hermano_id:")
                for admin in broken_leader_admins:
                    print(f"  - {admin.username}")
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

        print("\n=== DIAGNOSIS COMPLETE ===\n")

if __name__ == "__main__":
    asyncio.run(test_points_endpoint())
