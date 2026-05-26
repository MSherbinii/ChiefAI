from dotenv import load_dotenv
load_dotenv()  # must be before all imports that read env vars

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from models import ChatRequest, ChatResponse
from orchestrator import route_and_handle
from voice_intent import classify_voice_intent, VoiceIntent
from scoring.momentum import calculate_momentum
from brief.generator import generate_morning_brief
from connectors.gmail import sync_gmail
from connectors.github import sync_github
from connectors.whoop import sync_whoop
from connectors.imap_email import sync_imap
from feedback import record_approval_feedback, get_agent_performance, ApprovalOutcome
from embeddings import update_entity_embeddings, update_communication_embeddings
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from proactive import run_proactive_scan_all_users, run_proactive_scan
from supabase import create_client
import asyncio

scheduler = AsyncIOScheduler()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def run_daily_brief_for_all():
    """Run morning brief + momentum score for all connected users."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        users = sb.table('connector_tokens') \
            .select('user_id') \
            .eq('sync_status', 'ok') \
            .execute()
        user_ids = list(set(r['user_id'] for r in (users.data or [])))

        for uid in user_ids:
            try:
                await calculate_momentum(uid)
                await generate_morning_brief(uid)
            except Exception as e:
                print(f'Brief generation failed for {uid}: {e}')
    except Exception as e:
        print(f'Daily brief job error: {e}')


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(
        run_proactive_scan_all_users,
        'interval',
        hours=4,
        id='proactive_scan',
        replace_existing=True,
    )
    scheduler.add_job(
        run_daily_brief_for_all,
        'cron',
        hour=7, minute=0,
        id='daily_brief',
        replace_existing=True,
    )
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title='Chief Agent Service', version='0.1.0', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


class SyncRequest(BaseModel):
    user_id: str


class BriefRequest(BaseModel):
    user_id: str
    user_name: str = 'there'


class IMAPVerifyRequest(BaseModel):
    email: str
    password: str
    imap_host: str
    imap_port: int = 993


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'chief-agents'}


@app.post('/chat', response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    return await route_and_handle(request)


class VoiceClassifyRequest(BaseModel):
    transcript: str
    context: str = ''


@app.post('/voice/classify', response_model=VoiceIntent)
async def classify_voice(req: VoiceClassifyRequest) -> VoiceIntent:
    return classify_voice_intent(req.transcript, req.context)


@app.post('/sync/google')
async def sync_google(req: SyncRequest):
    asyncio.create_task(sync_gmail(req.user_id))
    return {'status': 'sync_started', 'connector': 'gmail'}


@app.post('/sync/github')
async def sync_github_route(req: SyncRequest):
    asyncio.create_task(sync_github(req.user_id))
    return {'status': 'sync_started', 'connector': 'github'}


@app.post('/sync/whoop')
async def sync_whoop_route(req: SyncRequest):
    asyncio.create_task(sync_whoop(req.user_id))
    return {'status': 'sync_started', 'connector': 'whoop'}


@app.post('/sync/imap_uni')
async def sync_imap_route(req: SyncRequest):
    asyncio.create_task(sync_imap(req.user_id))
    return {'status': 'sync_started', 'connector': 'imap_uni'}


@app.post('/score/momentum')
async def score_momentum(req: SyncRequest):
    result = await calculate_momentum(req.user_id)
    return result


@app.post('/brief/generate')
async def generate_brief(req: BriefRequest):
    result = await generate_morning_brief(req.user_id, req.user_name)
    return result


class FeedbackRequest(BaseModel):
    queue_item_id: str
    user_id: str
    approved: bool
    time_to_decision_seconds: Optional[float] = None


@app.post('/feedback/approval')
async def approval_feedback(req: FeedbackRequest):
    result = await record_approval_feedback(ApprovalOutcome(
        queue_item_id=req.queue_item_id,
        user_id=req.user_id,
        approved=req.approved,
        time_to_decision_seconds=req.time_to_decision_seconds,
    ))
    return result


@app.get('/feedback/performance/{user_id}/{agent}')
async def agent_performance(user_id: str, agent: str):
    return await get_agent_performance(user_id, agent)


@app.post('/embeddings/update')
async def update_embeddings(req: SyncRequest):
    entities = await update_entity_embeddings(req.user_id)
    comms = await update_communication_embeddings(req.user_id)
    return {'entities': entities, 'communications': comms}


@app.post('/proactive/scan')
async def proactive_scan(req: SyncRequest):
    result = await run_proactive_scan(req.user_id)
    return result


@app.post('/connectors/imap/verify')
async def verify_imap_route(req: IMAPVerifyRequest):
    import imaplib
    try:
        mail = imaplib.IMAP4_SSL(req.imap_host, req.imap_port)
        mail.login(req.email, req.password)
        mail.logout()
        return {'ok': True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'IMAP connection failed: {str(e)}')
