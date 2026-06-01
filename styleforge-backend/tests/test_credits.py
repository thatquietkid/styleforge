"""Tests for the credit system in StyleForge."""
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from common.models import User, CreditTransaction, RoleEnum
from genai.main import _check_and_deduct_credits

@pytest.mark.asyncio
async def test_new_user_starts_with_100_credits(db_session):
    """Verify that a brand new user starts with 100 credits by default."""
    user = User(email="new_credit_user@styleforge.ai", role=RoleEnum.user)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.credits == 100


@pytest.mark.asyncio
async def test_credit_history_recorded(db_session):
    """Verify that deducting credits records a CreditTransaction row."""
    user = User(email="tx_user@styleforge.ai", role=RoleEnum.user, credits=100)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Deduct 10 credits
    new_bal = await _check_and_deduct_credits(
        user=user,
        cost=10,
        description="Test generation",
        service="genai",
        db=db_session,
    )
    await db_session.commit()

    assert new_bal == 90
    assert user.credits == 90

    # Check transactions
    res = await db_session.execute(
        select(CreditTransaction).where(CreditTransaction.user_id == user.id)
    )
    txs = res.scalars().all()
    assert len(txs) == 1
    assert txs[0].amount == -10
    assert txs[0].description == "Test generation"
    assert txs[0].service == "genai"
    assert txs[0].balance_after == 90


@pytest.mark.asyncio
async def test_credit_deduction_insufficient(db_session):
    """Verify that _check_and_deduct_credits raises a 402 if credits are insufficient."""
    from fastapi import HTTPException
    user = User(email="poor_user@styleforge.ai", role=RoleEnum.user, credits=4)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    with pytest.raises(HTTPException) as exc_info:
        await _check_and_deduct_credits(
            user=user,
            cost=5,
            description="Style critique",
            service="genai",
            db=db_session,
        )
    
    assert exc_info.value.status_code == 402
    assert exc_info.value.detail["code"] == "insufficient_credits"
    assert user.credits == 4  # Unchanged
