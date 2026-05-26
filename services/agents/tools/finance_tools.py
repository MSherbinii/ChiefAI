"""
Finance tool implementations for Ledger agent.
Reads lg_finance data for spending analysis, subscription detection, affordability.
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class SpendingReport(BaseModel):
    period_days: int
    total_spent_cents: int
    total_spent_eur: float
    by_category: dict  # {category: amount_eur}
    top_merchant: Optional[str] = None
    vs_previous_period: Optional[float] = None  # percentage change


class SubscriptionReport(BaseModel):
    subscriptions: list[dict]  # [{name, amount_eur, last_seen, active}]
    total_monthly_eur: float
    unused: list[dict]  # subscriptions not seen in 30 days


class AffordabilityResult(BaseModel):
    can_afford: bool
    available_budget_eur: float
    reasoning: str
    suggestions: list[str]


async def get_spending_report(user_id: str, days: int = 30) -> SpendingReport:
    """Analyze spending patterns for the last N days."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        prev_cutoff = (datetime.now(timezone.utc) - timedelta(days=days * 2)).isoformat()

        # Current period
        current = sb.table('lg_finance') \
            .select('amount_cents, category, description') \
            .eq('user_id', user_id) \
            .eq('type', 'transaction') \
            .gte('transaction_at', cutoff) \
            .execute()

        # Previous period for comparison
        previous = sb.table('lg_finance') \
            .select('amount_cents') \
            .eq('user_id', user_id) \
            .eq('type', 'transaction') \
            .gte('transaction_at', prev_cutoff) \
            .lt('transaction_at', cutoff) \
            .execute()

        current_rows = current.data or []
        prev_rows = previous.data or []

        total_cents = sum(abs(r['amount_cents']) for r in current_rows if r.get('amount_cents', 0) < 0)
        prev_total = sum(abs(r['amount_cents']) for r in prev_rows if r.get('amount_cents', 0) < 0)

        by_category = {}
        for r in current_rows:
            if r.get('amount_cents', 0) < 0:
                cat = r.get('category') or 'other'
                by_category[cat] = by_category.get(cat, 0) + abs(r['amount_cents']) / 100

        pct_change = None
        if prev_total > 0:
            pct_change = ((total_cents - prev_total) / prev_total) * 100

        return SpendingReport(
            period_days=days,
            total_spent_cents=total_cents,
            total_spent_eur=round(total_cents / 100, 2),
            by_category={k: round(v, 2) for k, v in by_category.items()},
            vs_previous_period=round(pct_change, 1) if pct_change else None,
        )
    except Exception as e:
        return SpendingReport(period_days=days, total_spent_cents=0, total_spent_eur=0, by_category={})


async def detect_subscriptions(user_id: str) -> SubscriptionReport:
    """Detect recurring subscriptions and flag unused ones."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        subs = sb.table('lg_finance') \
            .select('description, amount_cents, last_used_at, recurring_period') \
            .eq('user_id', user_id) \
            .eq('is_subscription', True) \
            .execute()

        rows = subs.data or []
        now = datetime.now(timezone.utc)
        thirty_days_ago = (now - timedelta(days=30)).isoformat()

        subscriptions = []
        unused = []
        total_monthly = 0

        for r in rows:
            amount_eur = abs(r.get('amount_cents', 0)) / 100
            last_seen = r.get('last_used_at') or ''
            name = r.get('description', 'Unknown')
            period = r.get('recurring_period', 'monthly')

            monthly_cost = amount_eur if period == 'monthly' else amount_eur / 12
            total_monthly += monthly_cost

            sub_info = {
                'name': name,
                'amount_eur': amount_eur,
                'period': period,
                'last_seen': last_seen[:10] if last_seen else 'unknown',
            }
            subscriptions.append(sub_info)

            if last_seen and last_seen < thirty_days_ago:
                unused.append({
                    **sub_info,
                    'idle_days': (now - datetime.fromisoformat(last_seen.replace('Z', '+00:00'))).days,
                })

        return SubscriptionReport(
            subscriptions=subscriptions,
            total_monthly_eur=round(total_monthly, 2),
            unused=unused,
        )
    except Exception as e:
        return SubscriptionReport(subscriptions=[], total_monthly_eur=0, unused=[])


async def check_affordability(user_id: str, amount_eur: float, item: str) -> AffordabilityResult:
    """Can the user afford a specific purchase given current finances?"""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Get latest balance
        balance = sb.table('lg_finance') \
            .select('amount_cents, account') \
            .eq('user_id', user_id) \
            .eq('type', 'balance') \
            .order('transaction_at', desc=True) \
            .limit(5) \
            .execute()

        total_balance_eur = sum(r.get('amount_cents', 0) for r in (balance.data or [])) / 100

        # Get upcoming subscriptions (next 30 days)
        subs = await detect_subscriptions(user_id)
        monthly_obligations = subs.total_monthly_eur

        available = total_balance_eur - monthly_obligations - amount_eur
        can_afford = available > 0

        suggestions = []
        if not can_afford and subs.unused:
            recoverable = sum(s['amount_eur'] for s in subs.unused)
            suggestions.append(
                f'Cancel {len(subs.unused)} unused subscriptions (save €{recoverable:.0f}/mo)'
            )

        return AffordabilityResult(
            can_afford=can_afford,
            available_budget_eur=round(total_balance_eur - monthly_obligations, 2),
            reasoning=(
                f'Balance €{total_balance_eur:.0f} - monthly obligations €{monthly_obligations:.0f} = '
                f'€{total_balance_eur - monthly_obligations:.0f} available. '
                f'{item} costs €{amount_eur:.0f}.'
            ),
            suggestions=suggestions,
        )
    except Exception as e:
        return AffordabilityResult(
            can_afford=False,
            available_budget_eur=0,
            reasoning=f'Unable to check finances: {e}',
            suggestions=['Connect your bank account in Settings to get affordability analysis'],
        )
