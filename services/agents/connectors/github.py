import httpx
import os
from datetime import datetime, timezone
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def sync_github(user_id: str):
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    res = sb.table('connector_tokens').select('*').eq('user_id', user_id).eq('connector', 'github').maybe_single().execute()
    if not res.data:
        return

    pat = res.data['access_token']
    username = (res.data.get('extra') or {}).get('username', '')
    headers = {'Authorization': f'token {pat}', 'User-Agent': 'chief-app'}

    sb.table('connector_tokens').update({'sync_status': 'syncing'}).eq('user_id', user_id).eq('connector', 'github').execute()

    try:
        async with httpx.AsyncClient() as client:
            repos_res = await client.get(
                f'https://api.github.com/users/{username}/repos',
                headers=headers,
                params={'sort': 'pushed', 'per_page': 20},
            )
            repos = repos_res.json() if repos_res.status_code == 200 else []

        for repo in repos:
            if repo.get('fork'):
                continue
            sb.table('lg_projects').upsert({
                'user_id': user_id,
                'name': repo['name'],
                'type': 'github_repo',
                'status': 'archived' if repo.get('archived') else 'active',
                'tools': ['github'],
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,name').execute()

        # Fetch commits for top 5 non-fork repos
        active_repos = [r for r in repos if not r.get('fork')][:5]
        for repo in active_repos:
            async with httpx.AsyncClient() as client:
                commits_res = await client.get(
                    f'https://api.github.com/repos/{username}/{repo["name"]}/commits',
                    headers=headers,
                    params={'per_page': 10, 'author': username},
                )
                commits = commits_res.json() if commits_res.status_code == 200 else []

            for commit in commits:
                if not isinstance(commit, dict):
                    continue
                commit_date = commit.get('commit', {}).get('author', {}).get('date', '')
                message = commit.get('commit', {}).get('message', '')[:200]
                sha = commit.get('sha', '')[:12]
                if not commit_date:
                    continue

                sb.table('lg_health').upsert({
                    'user_id': user_id,
                    'metric': 'github_commit',
                    'value': {'repo': repo['name'], 'message': message, 'sha': sha},
                    'source': 'github',
                    'confidence': 'high',
                    'recorded_at': commit_date,
                }, on_conflict='user_id,metric,recorded_at').execute()

        sb.table('connector_tokens').update({
            'sync_status': 'ok',
            'last_synced_at': datetime.now(timezone.utc).isoformat(),
            'error_message': None,
        }).eq('user_id', user_id).eq('connector', 'github').execute()

    except Exception as e:
        sb.table('connector_tokens').update({
            'sync_status': 'error',
            'error_message': str(e)[:200],
        }).eq('user_id', user_id).eq('connector', 'github').execute()
        raise
