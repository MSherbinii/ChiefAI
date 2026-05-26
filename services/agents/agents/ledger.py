import re
import os
from agents.base import BaseAgent
from models import ChatRequest, ChatResponse
from llm import get_client, AGENT_MODEL
from tools.finance_tools import get_spending_report, detect_subscriptions, check_affordability

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class LedgerAgent(BaseAgent):
    name = 'Ledger'
    description = 'Finance: spending patterns, subscriptions, budget, affordability decisions.'

    async def fetch_context(self, user_id: str) -> str:
        if not user_id:
            return 'No finance data available. Connect a bank account in Settings.'

        lines = ['=== FINANCE CONTEXT ===']

        # Spending report
        spending = await get_spending_report(user_id, days=30)
        if spending.total_spent_eur > 0:
            lines.append(f'SPENDING (30d): €{spending.total_spent_eur:.0f} total')
            if spending.vs_previous_period is not None:
                trend = '+' if spending.vs_previous_period > 0 else ''
                lines.append(f'  vs previous 30d: {trend}{spending.vs_previous_period:.0f}%')
            if spending.by_category:
                top_cats = sorted(spending.by_category.items(), key=lambda x: x[1], reverse=True)[:3]
                for cat, amt in top_cats:
                    lines.append(f'  {cat}: €{amt:.0f}')
        else:
            lines.append('No spending data yet. Connect a bank account in Settings.')

        # Subscriptions
        subs = await detect_subscriptions(user_id)
        if subs.subscriptions:
            lines.append(
                f'SUBSCRIPTIONS: €{subs.total_monthly_eur:.0f}/mo total ({len(subs.subscriptions)} active)'
            )
            if subs.unused:
                names = ', '.join(s['name'] for s in subs.unused[:3])
                lines.append(f'  UNUSED ({len(subs.unused)}): {names}')

        return '\n'.join(lines)

    async def handle(self, request: ChatRequest) -> ChatResponse:
        client = get_client()
        context = await self.fetch_context(request.user_id or '')

        # Detect affordability query and enrich context
        msg_lower = request.message.lower()
        if any(kw in msg_lower for kw in ['can i afford', 'can i buy', 'how much can i spend']):
            amounts = re.findall(r'€?(\d+(?:\.\d+)?)', request.message)
            if amounts and request.user_id:
                amount = float(amounts[0])
                afford = await check_affordability(request.user_id, amount, request.message)
                context += f'\nAFFORDABILITY CHECK for €{amount}: {"YES" if afford.can_afford else "NO"}'
                context += f'\n{afford.reasoning}'
                if afford.suggestions:
                    context += '\nSUGGESTIONS: ' + '; '.join(afford.suggestions)

        messages = [{'role': m.role, 'content': m.content} for m in request.history]
        messages.append({'role': 'user', 'content': request.message})

        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=512,
            system=f'{self.system_prompt}\n\n{context}',
            messages=messages,
        )
        return ChatResponse(reply=response.content[0].text, agent='Ledger')
