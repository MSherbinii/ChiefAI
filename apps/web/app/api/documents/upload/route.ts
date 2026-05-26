import { NextResponse } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function POST(request: Request) {
  const supabase = await createClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });

  const formData = await request.formData();
  const file = formData.get('file') as File;
  const docType = formData.get('type') as string ?? 'document';

  if (!file) return NextResponse.json({ error: 'No file' }, { status: 400 });

  // Upload to Supabase Storage (documents bucket)
  const ext = file.name.split('.').pop() ?? 'jpg';
  const path = `${user.id}/${Date.now()}.${ext}`;

  const arrayBuffer = await file.arrayBuffer();
  const { data: uploadData, error: uploadError } = await supabase.storage
    .from('documents')
    .upload(path, arrayBuffer, { contentType: file.type });

  if (uploadError) {
    return NextResponse.json({ error: uploadError.message }, { status: 500 });
  }

  // Get public URL
  const { data: { publicUrl } } = supabase.storage.from('documents').getPublicUrl(path);

  // Trigger OCR extraction via agent service
  const agentUrl = process.env.AGENT_SERVICE_URL ?? 'http://localhost:8001';
  const extractRes = await fetch(`${agentUrl}/documents/extract`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: user.id,
      storage_path: path,
      doc_type: docType,
      file_url: publicUrl,
    }),
  }).catch(() => null);

  let extracted = null;
  if (extractRes?.ok) {
    extracted = await extractRes.json();
  }

  return NextResponse.json({
    ok: true,
    storage_path: path,
    doc_type: docType,
    extracted,
  });
}
