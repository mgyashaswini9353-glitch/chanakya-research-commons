import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  Bookmark,
  BookmarkCheck,
  BookOpen,
  ExternalLink,
  FileText,
  MessageSquare,
  Save,
  Users,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  CardSkeleton,
  formatSourceLabel,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

export default function PaperDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { showToast } = useToast();

  const [paper, setPaper] = useState<any>(null);
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedCol, setSelectedCol] = useState<string>('');
  const [notes, setNotes] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/api/papers/${id}`),
      user ? api.get('/api/collections').catch(() => []) : Promise.resolve([]),
    ])
      .then(([p, cols]) => {
        setPaper(p);
        setNotes(p.my_private_notes || '');
        setSelectedCol(p.my_collection_id ? String(p.my_collection_id) : '');
        setCollections(cols || []);
      })
      .finally(() => setLoading(false));
  }, [id, user]);

  const handleSaveOrUpdate = async () => {
    if (!user || !paper) return;
    setSaving(true);
    try {
      const res = await api.post('/api/library/save', {
        paper_id: paper.id,
        collection_id: selectedCol ? Number(selectedCol) : null,
        private_notes: notes,
      });
      setPaper({ ...paper, ...res.paper });
      showToast('Saved to your personal library');
    } catch (err: any) {
      showToast(err.message || 'Could not save publication', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleUnsave = async () => {
    if (!user || !paper) return;
    await api.del(`/api/library/save/${paper.id}`);
    setPaper({
      ...paper,
      is_saved_by_me: false,
      save_count: Math.max(0, (paper.save_count || 1) - 1),
    });
    showToast('Removed from your personal library', 'info');
  };

  if (loading) return <CardSkeleton rows={3} />;
  if (!paper) {
    return (
      <div className="surface-card p-10 text-center text-sm text-[#697386]">
        Publication not found.
      </div>
    );
  }

  const sourcesList = Array.from(
    new Set((paper.sources || []).map((s: any) => formatSourceLabel(s.source)).filter(Boolean))
  );

  return (
    <div className="space-y-6">
      <Link to="/discover" className="inline-flex items-center gap-1.5 text-xs font-medium text-[#697386] hover:text-[#142B4A]">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to Explore
      </Link>

      <div className="grid lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-8 space-y-6">
          <article className="surface-card p-6 sm:p-8 space-y-5">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              {paper.publication_year && <span className="font-semibold text-[#8E6914]">{paper.publication_year}</span>}
              {paper.venue && (
                <>
                  <span className="text-[#DCD7CA]">·</span>
                  <span className="font-medium text-[#3B485C]">{paper.venue}</span>
                </>
              )}
              {paper.in_university_library && (
                <>
                  <span className="text-[#DCD7CA]">·</span>
                  <span className="sage-badge">
                    Saved by {paper.save_count} {paper.save_count === 1 ? 'member' : 'members'}
                  </span>
                </>
              )}
            </div>

            <h1 className="text-2xl sm:text-[26px] font-semibold text-[#142B4A] leading-snug tracking-tight">
              {paper.title}
            </h1>

            <div className="text-sm text-[#3B485C]">
              {(paper.authors || []).join(', ') || 'Authors not listed'}
            </div>

            <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-[#697386] border-y border-[#EFECE4] py-3">
              {paper.citation_count > 0 && (
                <span><strong className="text-[#263247]">{paper.citation_count.toLocaleString()}</strong> citations</span>
              )}
              {paper.doi && <span>DOI: <span className="text-[#263247]">{paper.doi}</span></span>}
              {paper.arxiv_id && <span>arXiv: <span className="text-[#263247]">{paper.arxiv_id}</span></span>}
              {sourcesList.length > 0 && (
                <span>Indexed in: <span className="text-[#263247]">{sourcesList.join(', ')}</span></span>
              )}
            </div>

            <div className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-[#697386]">Abstract</h2>
              <p className="text-[14.5px] text-[#263247] leading-[1.75] whitespace-pre-line">
                {paper.abstract || 'No abstract is available for this publication.'}
              </p>
            </div>

            {(paper.topics || []).length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {paper.topics.map((t: string) => (
                  <Link
                    key={t}
                    to={`/search?q=${encodeURIComponent(t.replace(/-/g, ' '))}`}
                    className="topic-pill"
                  >
                    {formatTopicLabel(t)}
                  </Link>
                ))}
              </div>
            )}

            <div className="flex flex-wrap gap-2.5 pt-2">
              {paper.url && (
                <a href={paper.url} target="_blank" rel="noreferrer" className="btn-primary text-xs">
                  Read Publication <ExternalLink className="h-3.5 w-3.5" />
                </a>
              )}
              {paper.pdf_url && (
                <a href={paper.pdf_url} target="_blank" rel="noreferrer" className="btn-secondary text-xs">
                  <FileText className="h-3.5 w-3.5" /> Open PDF
                </a>
              )}
              {user && (
                <Link to={`/discussions/new?paper=${paper.id}`} className="btn-secondary text-xs">
                  <MessageSquare className="h-3.5 w-3.5" /> Discuss with Community
                </Link>
              )}
            </div>
          </article>

          {(paper.also_saved?.items || []).length > 0 && (
            <section className="surface-card p-6 space-y-4">
              <div>
                <h2 className="text-base font-semibold text-[#142B4A]">
                  People who saved this paper also explored
                </h2>
                <p className="text-xs text-[#697386] mt-0.5">
                  Related publications frequently saved together by Chanakya University members.
                </p>
              </div>
              <div className="grid sm:grid-cols-2 gap-3.5">
                {paper.also_saved.items.map((item: any) => (
                  <Link
                    key={item.id}
                    to={`/papers/${item.id}`}
                    className="rounded-xl border border-[#E6E2D8] p-4 hover:border-[#D6AA35] hover:bg-[#FAF8F2]/60 transition-colors space-y-1.5"
                  >
                    <div className="text-sm font-medium text-[#142B4A] line-clamp-2 leading-snug">
                      {item.title}
                    </div>
                    <div className="text-xs text-[#697386]">
                      {(item.authors || []).slice(0, 2).join(', ')}
                      {item.publication_year ? ` · ${item.publication_year}` : ''}
                    </div>
                    {item.save_count > 0 && (
                      <div className="text-[11px] text-[#2E5438] font-medium pt-0.5">
                        Saved by {item.save_count} campus {item.save_count === 1 ? 'member' : 'members'}
                      </div>
                    )}
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="lg:col-span-4 space-y-4">
          <div className="surface-card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#142B4A] flex items-center gap-2">
              {paper.is_saved_by_me ? (
                <BookmarkCheck className="h-4 w-4 text-[#A67E1E]" />
              ) : (
                <Bookmark className="h-4 w-4 text-[#697386]" />
              )}
              My Library & Private Notes
            </h3>

            {user ? (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-[#3B485C] mb-1">Personal collection</label>
                  <select
                    value={selectedCol}
                    onChange={(e) => setSelectedCol(e.target.value)}
                    className="input-field bg-white text-xs py-2"
                  >
                    <option value="">All Saved Papers</option>
                    {collections.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#3B485C] mb-1">Private notes</label>
                  <textarea
                    rows={4}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Capture reading notes or ideas for your work..."
                    className="input-field text-xs"
                  />
                </div>

                <div className="flex gap-2">
                  <button onClick={handleSaveOrUpdate} disabled={saving} className="btn-primary flex-1 text-xs py-2">
                    <Save className="h-3.5 w-3.5" />
                    {paper.is_saved_by_me ? 'Save Changes' : 'Save to Library'}
                  </button>
                  {paper.is_saved_by_me && (
                    <button onClick={handleUnsave} className="btn-secondary text-xs py-2 text-rose-700 hover:bg-rose-50">
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-[#697386]">
                <Link to="/login" className="font-medium text-[#142B4A] underline">Sign in</Link> to save this publication and keep private notes.
              </p>
            )}
          </div>

          <div className="surface-card p-5 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[#142B4A] flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-[#8E6914]" />
              Saved on Campus ({paper.save_count || 0})
            </h3>
            {(paper.saved_by_members || []).length === 0 ? (
              <p className="text-xs text-[#697386]">No members have saved this paper yet.</p>
            ) : (
              <div className="space-y-2">
                {paper.saved_by_members.map((m: any) => (
                  <Link
                    key={m.id}
                    to={`/researchers/${m.id}`}
                    className="flex items-center gap-2.5 p-2 rounded-lg hover:bg-[#FAF8F2] transition-colors"
                  >
                    <div className="h-7 w-7 rounded-full bg-[#E9EFE8] text-[#142B4A] flex items-center justify-center text-[10px] font-semibold">
                      {getInitials(m.full_name)}
                    </div>
                    <div className="min-w-0">
                      <div className="text-xs font-medium text-[#142B4A] truncate">{m.full_name}</div>
                      <div className="text-[11px] text-[#697386] capitalize">{m.role} · {m.department_code}</div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="surface-card p-5 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[#142B4A] flex items-center gap-1.5">
              <BookOpen className="h-3.5 w-3.5 text-[#697386]" /> Related Discussions
            </h3>
            {(paper.related_discussions || []).length === 0 ? (
              <p className="text-xs text-[#697386]">No discussions mention this paper yet.</p>
            ) : (
              <div className="space-y-2">
                {paper.related_discussions.map((d: any) => (
                  <Link
                    key={d.id}
                    to={`/discussions?post=${d.id}`}
                    className="block p-2.5 rounded-lg border border-[#F0ECE2] hover:border-[#D6AA35] transition-colors"
                  >
                    <div className="text-xs font-medium text-[#142B4A]">{d.title}</div>
                    <div className="text-[11px] text-[#697386] mt-0.5">
                      {d.upvote_count} likes · {d.comment_count} replies
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
