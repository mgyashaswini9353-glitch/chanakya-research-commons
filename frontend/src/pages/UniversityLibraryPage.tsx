import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Bookmark,
  BookMarked,
  BookOpen,
  Clock,
  FolderOpen,
  MessageSquare,
  Plus,
  X,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import PaperCard from '../components/PaperCard';
import { CardSkeleton, EmptyState, formatRelativeDate } from '../components/UIPrimitives';

export default function UniversityLibraryPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialTab =
    (searchParams.get('tab') as 'my' | 'university' | 'posts' | 'recent') ||
    (user ? 'my' : 'university');
  const [tab, setTab] = useState<'my' | 'university' | 'posts' | 'recent'>(initialTab);
  const [sort, setSort] = useState('saves');
  const [papers, setPapers] = useState<any[]>([]);
  const [savedPosts, setSavedPosts] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  const [showAddModal, setShowAddModal] = useState(false);
  const [addForm, setAddForm] = useState({
    doi: '',
    arxiv_id: '',
    url: '',
    title: '',
    topics: '',
    private_notes: '',
  });
  const [submitting, setSubmitting] = useState(false);

  const load = async (activeTab = tab) => {
    setLoading(true);
    try {
      if (activeTab === 'my' && user) {
        const res = await api.get('/api/library/my');
        setPapers(res.items || []);
        setTotal(res.total || (res.items || []).length);
      } else if (activeTab === 'posts' && user) {
        const res = await api.get('/api/posts?feed=saved&limit=30');
        setSavedPosts(res.items || []);
        setTotal((res.items || []).length);
      } else if (activeTab === 'recent' && user) {
        const res = await api.get('/api/library/recently-viewed?limit=20');
        setPapers(res.items || []);
        setTotal((res.items || []).length);
      } else {
        const res = await api.get(`/api/papers?only_library=true&sort=${sort}&limit=40`);
        setPapers(res.items || []);
        setTotal(res.total || 0);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load(tab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, sort, user]);

  const handleAddPaper = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm.doi && !addForm.arxiv_id && !addForm.url && !addForm.title) {
      showToast('Please enter a DOI, arXiv ID, URL, or title.', 'error');
      return;
    }
    setSubmitting(true);
    try {
      await api.post('/api/papers/add-by-identifier', {
        doi: addForm.doi || null,
        arxiv_id: addForm.arxiv_id || null,
        url: addForm.url || null,
        title: addForm.title || null,
        topics: addForm.topics.split(',').map((t) => t.trim()).filter(Boolean),
        private_notes: addForm.private_notes,
      });
      setAddForm({ doi: '', arxiv_id: '', url: '', title: '', topics: '', private_notes: '' });
      setShowAddModal(false);
      showToast('Added to your library and the shared Chanakya library');
      load(tab);
    } catch (err: any) {
      showToast(err.message || 'Could not add publication', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const switchTab = (next: 'my' | 'university' | 'posts' | 'recent') => {
    setTab(next);
    setSearchParams({ tab: next });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">My Library</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Keep your saved papers, bookmarked community posts, collections, and shared university readings organized.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {user && (
            <>
              <Link to="/collections" className="btn-secondary text-xs">
                <FolderOpen className="h-3.5 w-3.5" /> Collections
              </Link>
              <button onClick={() => setShowAddModal(true)} className="btn-primary text-xs">
                <Plus className="h-3.5 w-3.5" /> Add Publication
              </button>
            </>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E6E2D8]">
        <div className="flex items-center gap-1 overflow-x-auto">
          {user && (
            <button
              onClick={() => switchTab('my')}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap ${
                tab === 'my' ? 'border-[#D6AA35] text-[#142B4A]' : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              <BookMarked className="h-4 w-4" /> Saved Papers
            </button>
          )}
          {user && (
            <button
              onClick={() => switchTab('posts')}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap ${
                tab === 'posts' ? 'border-[#D6AA35] text-[#142B4A]' : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              <Bookmark className="h-4 w-4" /> Saved Posts
            </button>
          )}
          <button
            onClick={() => switchTab('university')}
            className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap ${
              tab === 'university' ? 'border-[#D6AA35] text-[#142B4A]' : 'border-transparent text-[#697386] hover:text-[#142B4A]'
            }`}
          >
            <BookOpen className="h-4 w-4" /> University Library
          </button>
          {user && (
            <button
              onClick={() => switchTab('recent')}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap ${
                tab === 'recent' ? 'border-[#D6AA35] text-[#142B4A]' : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              <Clock className="h-4 w-4" /> Recently Viewed
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 pb-2 sm:pb-0">
          <span className="text-xs text-[#697386]">{total} items</span>
          {tab === 'university' && (
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value)}
              className="input-field w-auto text-xs bg-white py-1.5"
            >
              <option value="saves">Most Saved on Campus</option>
              <option value="citations">Most Cited</option>
              <option value="recent">Newest First</option>
            </select>
          )}
        </div>
      </div>

      {/* Content */}
      {loading ? (
        <CardSkeleton rows={4} />
      ) : tab === 'posts' ? (
        savedPosts.length === 0 ? (
          <EmptyState
            icon={MessageSquare}
            title="No saved community posts yet"
            description="Bookmark helpful discussions from the Home or Community feed to revisit them here."
            action={<Link to="/discussions" className="btn-primary text-xs">Explore Community</Link>}
          />
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {savedPosts.map((po) => (
              <Link key={po.id} to={`/discussions?post=${po.id}`} className="surface-card-interactive p-5 space-y-2 block">
                <div className="text-sm font-semibold text-[#142B4A]">{po.title}</div>
                <p className="text-xs text-[#3B485C] line-clamp-3">{po.content}</p>
                <div className="text-[11px] text-[#697386] pt-1">
                  {po.author?.full_name} · {formatRelativeDate(po.created_at)} · {po.upvote_count} likes · {po.comment_count} replies
                </div>
              </Link>
            ))}
          </div>
        )
      ) : papers.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title={tab === 'my' ? 'Your personal library is empty' : tab === 'recent' ? 'No recently viewed papers' : 'No library items yet'}
          description="Explore publications and save them here with your own private notes and collections."
          action={<Link to="/discover" className="btn-primary text-xs">Explore Research</Link>}
        />
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {papers.map((p) => (
            <PaperCard
              key={p.id}
              paper={p}
              onSaveChanged={() => {
                if (tab === 'my') load('my');
              }}
            />
          ))}
        </div>
      )}

      {/* Add Publication Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/45 p-4">
          <div className="surface-card max-w-lg w-full p-6 space-y-4 shadow-dropdown">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-[#142B4A]">Add a Publication</h2>
                <p className="text-xs text-[#697386]">
                  Paste a DOI, arXiv ID, or URL to resolve citation details automatically.
                </p>
              </div>
              <button onClick={() => setShowAddModal(false)} className="text-[#8A92A0] hover:text-[#142B4A]">
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleAddPaper} className="space-y-3">
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#263247] mb-1">DOI</label>
                  <input value={addForm.doi} onChange={(e) => setAddForm({ ...addForm, doi: e.target.value })} placeholder="10.48550/arXiv.2005.11401" className="input-field text-xs" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#263247] mb-1">arXiv ID</label>
                  <input value={addForm.arxiv_id} onChange={(e) => setAddForm({ ...addForm, arxiv_id: e.target.value })} placeholder="2005.11401" className="input-field text-xs" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Publication URL</label>
                <input value={addForm.url} onChange={(e) => setAddForm({ ...addForm, url: e.target.value })} placeholder="https://..." className="input-field text-xs" />
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#263247] mb-1">Title (optional)</label>
                  <input value={addForm.title} onChange={(e) => setAddForm({ ...addForm, title: e.target.value })} placeholder="If not auto-resolved" className="input-field text-xs" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#263247] mb-1">Topics</label>
                  <input value={addForm.topics} onChange={(e) => setAddForm({ ...addForm, topics: e.target.value })} placeholder="Machine Learning, Healthcare" className="input-field text-xs" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Private notes</label>
                <textarea rows={2} value={addForm.private_notes} onChange={(e) => setAddForm({ ...addForm, private_notes: e.target.value })} placeholder="Optional reading notes..." className="input-field text-xs" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAddModal(false)} className="btn-secondary text-xs">Cancel</button>
                <button type="submit" disabled={submitting} className="btn-primary text-xs">
                  {submitting ? 'Adding...' : 'Save to Library'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
