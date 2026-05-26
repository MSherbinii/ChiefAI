-- Create documents storage bucket (via Supabase dashboard)
-- This SQL creates the bucket configuration if using Supabase MCP
-- The actual bucket creation must be done via Supabase dashboard:
-- Storage → New bucket → "documents" → Private (not public)

-- Add storage policy for documents
insert into storage.buckets (id, name, public)
values ('documents', 'documents', false)
on conflict (id) do nothing;

create policy "Users access own documents"
  on storage.objects for all
  using (bucket_id = 'documents' and auth.uid()::text = (storage.foldername(name))[1]);
