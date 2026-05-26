from dotenv import load_dotenv
load_dotenv()  # must be before all imports that read env vars

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from models import ChatRequest, ChatResponse
from orchestrator import route_and_handle
from scoring.momentum import calculate_momentum
from brief.generator import generate_morning_brief
from connectors.gmail import sync_gmail
from connectors.github import sync_github
from connectors.whoop import sync_whoop
from connectors.imap_email import sync_imap
from feedback import record_approval_feedback, get_agent_performance, ApprovalOutcome
import asyncio

app = FastAPI(title='Chief Agent Service', version='0.1.0')

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
