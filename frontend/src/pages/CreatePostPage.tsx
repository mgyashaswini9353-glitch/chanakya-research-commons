import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';

export default function CreatePostPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();

  const [papers, setPapers] = useState<any[]>([]);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [paperId, setPaperId] = useState(searchParams.get('paper') || '');
  const [attachedUrl, setAttachedUrl] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.get('/api/papers?only_library=true&limit=60').then((r) => setPapers(r.items || [])).catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (title.trim().length < 3 || content.trim().length < 5) {
      setError('Please enter a descriptive headline and post body.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await api.post('/api/posts', {
        title: title.trim(),
        content: content.trim(),
        tags: tags
          .split(',')
          .map((t) => t.trim().toLowerCase().replace(/\s+/g, '-'))
          .filter(Boolean),
        attached_paper_id: paperId ? Number(paperId) : null,
        attached_url: attachedUrl.trim(),
      });
      showToast('Discussion published');
      navigate(`/discussions?post=${res.id}`);
    } catch (err: any) {
      setError(err.message || 'Unable to publish discussion');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-5">
      <Link to="/discussions" className="inline-flex items-center gap-1.5 text-xs font-medium text-[#697386] hover:text-[#142B4A]">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Community
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Start a Research Discussion</h1>
        <p className="text-sm text-[#697386] mt-0.5">
          Share reading notes, pose methodology questions, or attach a publication from the university library.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="surface-card p-6 space-y-4">
        {error && (
          <div className="rounded-md bg-rose-50 border border-rose-200 px-3.5 py-2.5 text-xs text-rose-800">
            {error}
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">Discussion headline *</label>
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Reading group takeaways on scalable protein folding benchmarks"
            className="input-field"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">Discussion body *</label>
          <textarea
            required
            rows={6}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Share your observations, questions, datasets, or hypotheses..."
            className="input-field"
          />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Topics (comma separated)</label>
            <input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Bioinformatics, Machine Learning"
              className="input-field text-xs"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Attach paper from library (optional)</label>
            <select
              value={paperId}
              onChange={(e) => setPaperId(e.target.value)}
              className="input-field bg-white text-xs"
            >
              <option value="">None</option>
              {papers.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title.slice(0, 72)} ({p.publication_year || 'Recent'})
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">External link (optional)</label>
          <input
            value={attachedUrl}
            onChange={(e) => setAttachedUrl(e.target.value)}
            placeholder="https://..."
            className="input-field text-xs"
          />
        </div>

        <div className="flex justify-end gap-2.5 pt-2">
          <button type="button" onClick={() => navigate('/discussions')} className="btn-secondary text-xs">
            Cancel
          </button>
          <button type="submit" disabled={submitting} className="btn-primary text-xs">
            {submitting ? 'Publishing...' : 'Publish Discussion'}
          </button>
        </div>
      </form>
    </div>
  );
}
