"""
Real tool implementations for Pulse (health) agent.
These are callable functions that read/write to the Life Graph.
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class WorkoutLogInput(BaseModel):
    user_id: str
    date: str  # ISO date
    exercises: list[dict]  # [{name, sets, reps, weight_kg}]
    notes: Optional[str] = None
    perceived_effort: Optional[int] = None  # 1-10


class NutritionLogInput(BaseModel):
    user_id: str
    meal_description: str
    estimated_calories: Optional[int] = None
    estimated_protein_g: Optional[float] = None
    confidence: str = 'low'  # food photos are always low confidence


class HealthToolResult(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


async def log_workout(input: WorkoutLogInput) -> HealthToolResult:
    """Log a workout session to lg_health."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('lg_health').upsert({
            'user_id': input.user_id,
            'metric': 'workout_manual',
            'value': {
                'exercises': input.exercises,
                'notes': input.notes,
                'perceived_effort': input.perceived_effort,
                'source': 'voice_capture',
            },
            'source': 'manual',
            'confidence': 'high',
            'recorded_at': input.date or datetime.now(timezone.utc).isoformat(),
        }, on_conflict='user_id,metric,recorded_at').execute()
        return HealthToolResult(success=True, message=f'Logged workout with {len(input.exercises)} exercises')
    except Exception as e:
        return HealthToolResult(success=False, message=str(e))


async def log_nutrition(input: NutritionLogInput) -> HealthToolResult:
    """Log a meal/nutrition entry to lg_health."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('lg_health').insert({
            'user_id': input.user_id,
            'metric': 'nutrition',
            'value': {
                'description': input.meal_description,
                'estimated_calories': input.estimated_calories,
                'estimated_protein_g': input.estimated_protein_g,
            },
            'source': 'manual',
            'confidence': input.confidence,
            'recorded_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
        cal_str = f', ~{input.estimated_calories} kcal' if input.estimated_calories else ''
        return HealthToolResult(success=True, message=f'Logged: {input.meal_description}{cal_str}')
    except Exception as e:
        return HealthToolResult(success=False, message=str(e))


async def get_recovery_trend(user_id: str, days: int = 7) -> dict:
    """Get recovery trend for last N days."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        result = sb.table('lg_health') \
            .select('value, recorded_at') \
            .eq('user_id', user_id) \
            .eq('metric', 'recovery') \
            .gte('recorded_at', cutoff) \
            .order('recorded_at', desc=False) \
            .execute()

        if not result.data:
            return {'trend': 'no_data', 'scores': [], 'avg': None}

        scores = [r['value'].get('recovery_score', 0) for r in result.data]
        avg = sum(scores) / len(scores)

        # Trend: compare first half vs second half
        mid = len(scores) // 2
        if mid > 0:
            first_half_avg = sum(scores[:mid]) / mid
            second_half_avg = sum(scores[mid:]) / len(scores[mid:])
            if second_half_avg > first_half_avg + 5:
                trend = 'improving'
            elif second_half_avg < first_half_avg - 5:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'scores': scores,
            'avg': round(avg, 1),
            'latest': scores[-1] if scores else None,
            'days': days,
        }
    except Exception as e:
        return {'trend': 'error', 'error': str(e)}
