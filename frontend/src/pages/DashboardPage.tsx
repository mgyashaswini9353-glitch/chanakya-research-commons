import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  Bookmark,
  BookmarkCheck,
  BookMarked,
  BookOpen,
  Clock,
  Edit2,
  FolderOpen,
  Heart,
  MessageSquare,
  PenSquare,
  Trash2,
  TrendingUp,
  UserCheck,
  UserPlus,
  Users,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import PaperCard from '../components/PaperCard';
import {
  CardSkeleton,
  ConfirmDialog,
  EmptyState,
  formatRelativeDate,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

export default function DashboardPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [feedMode, setFeedMode] = useState<'personalized' | 'following' | 'all' | 'saved'>(
    user ? 'personalized' : 'all'
  );
  const [posts, setPosts] = useState<any[]>([]);
  const [feedLoading, setFeedLoading] = useState(true);
  const [recPapers, setRecPapers] = useState<any[]>([]);
  const [recResearchers, setRecResearchers] = useState<any[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [recentlyViewed, setRecentlyViewed] = useState<any[]>([]);
  const [collectionsCount, setCollectionsCount] = useState(0);
  const [followedMap, setFollowedMap] = useState<Record<number, boolean>>({});

  // Post composer
  const [composerOpen, setComposerOpen] = useState(false);
  const [postTitle, setPostTitle] = useState('');
  const [postContent, setPostContent] = useState('');
  const [postTags, setPostTags] = useState('');
  const [posting, setPosting] = useState(false);

  // Edit / Delete state
  const [editingPost, setEditingPost] = useState<any>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  const loadFeed = async (mode = feedMode) => {
    setFeedLoading(true);
    try {
      const res = await api.get(`/api/posts?feed=${mode}&limit=12`);
      setPosts(res.items || []);
    } finally {
      setFeedLoading(false);
    }
  };

  useEffect(() => {
    loadFeed(feedMode);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feedMode, user]);

  useEffect(() => {
    api
      .get('/api/trends?window_days=14')
      .then((t) => setTrends(t.trending_topics || []))
      .catch(() => {});

    if (user) {
      Promise.all([
        api.get('/api/recommendations/papers?limit=4').catch(() => ({ recommendations: [] })),
        api.get('/api/recommendations/researchers?limit=4').catch(() => ({ recommendations: [] })),
        api.get('/api/library/recently-viewed?limit=4').catch(() => ({ items: [] })),
        api.get('/api/collections').catch(() => []),
      ]).then(([rp, rr, rv, cols]) => {
        setRecPapers(rp.recommendations || []);
        setRecResearchers(rr.recommendations || []);
        setRecentlyViewed(rv.items || []);
        setCollectionsCount((cols || []).length);
      });
    } else {
      Promise.all([
        api.get('/api/papers?only_library=true&sort=saves&limit=4').catch(() => ({ items: [] })),
        api.get('/api/users?limit=4').catch(() => []),
      ]).then(([rp, ru]) => {
        setRecPapers(rp.items || []);
        setRecResearchers(ru || []);
      });
    }
  }, [user]);

  const handlePublish = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!postTitle.trim() || !postContent.trim()) return;
    setPosting(true);
    try {
      await api.post('/api/posts', {
        title: postTitle.trim(),
        content: postContent.trim(),
        tags: postTags
          .split(',')
          .map((t) => t.trim().toLowerCase().replace(/\s+/g, '-'))
          .filter(Boolean),
      });
      setPostTitle('');
      setPostContent('');
      setPostTags('');
      setComposerOpen(false);
      showToast('Shared with the Chanakya community');
      loadFeed(feedMode);
    } catch (err: any) {
      showToast(err.message || 'Could not publish post', 'error');
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (postId: number) => {
    if (!user) {
      navigate('/login');
      return;
    }
    const res = await api.post(`/api/posts/${postId}/upvote`);
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, has_upvoted: res.upvoted, upvote_count: res.upvote_count } : p))
    );
  };

  const handleSavePost = async (postId: number) => {
    if (!user) {
      navigate('/login');
      return;
    }
    const res = await api.post(`/api/posts/${postId}/save`);
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, is_saved_by_me: res.saved } : p))
    );
    showToast(res.saved ? 'Post saved to your library' : 'Removed from saved posts', res.saved ? 'success' : 'info');
    if (feedMode === 'saved' && !res.saved) loadFeed('saved');
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPost) return;
    await api.patch(`/api/posts/${editingPost.id}`, {
      title: editTitle.trim(),
      content: editContent.trim(),
    });
    setEditingPost(null);
    showToast('Post updated');
    loadFeed(feedMode);
  };

  const handleConfirmDelete = async () => {
    if (!deleteTargetId) return;
    await api.del(`/api/posts/${deleteTargetId}`);
    setDeleteTargetId(null);
    showToast('Post deleted', 'info');
    loadFeed(feedMode);
  };

  const handleFollow = async (uid: number, name: string) => {
    if (!user) {
      navigate('/login');
      return;
    }
    await api.post(`/api/users/${uid}/follow`);
    setFollowedMap((prev) => ({ ...prev, [uid]: true }));
    showToast(`Now following ${name}`);
  };

  return (
    <div className="space-y-6">
      {/* Welcoming Chanakya University Campus Banner (Compact & Balanced) */}
      <section className="surface-card overflow-hidden grid md:grid-cols-12 items-center">
        <div className="md:col-span-7 p-6 sm:p-7 space-y-3">
          <div className="gold-badge">Chanakya University · Campus Research Community</div>
          <h1 className="text-2xl sm:text-[28px] font-semibold text-[#142B4A] tracking-tight leading-snug">
            Ideas grow when we share them.
          </h1>
          <p className="text-sm text-[#697386] leading-relaxed max-w-xl">
            Connect with curious minds, discover research and be part of the conversations shaping tomorrow.
          </p>
          <div className="flex flex-wrap items-center gap-2.5 pt-1">
            <Link to="/discussions" className="btn-primary text-xs py-2 px-4">
              Explore Community
            </Link>
            <Link to="/discover" className="btn-secondary text-xs py-2 px-4">
              Discover Research
            </Link>
          </div>
        </div>
        <div className="md:col-span-5 h-44 md:h-full">
          <img
            src="/images/chanakya/CU-logo.jpg"
            alt="Chanakya University Administration Block"
            className="w-full h-full object-cover"
          />
        </div>
      </section>

      {/* Main 3-Column Campus Community Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT SIDEBAR: Member Card, Library, Interests, Recently Viewed */}
        <aside className="lg:col-span-3 space-y-4">
          {user ? (
            <>
              <div className="surface-card overflow-hidden">
                <div className="h-12 bg-[#142B4A] relative">
                  <div className="absolute bottom-0 inset-x-0 h-1 bg-[#D6AA35]" />
                </div>
                <div className="px-4 pb-4 -mt-6 space-y-3 relative">
                  <Link to={`/researchers/${user.id}`} className="inline-block">
                    <div className="h-12 w-12 rounded-full bg-[#142B4A] text-[#FBF5E4] border-2 border-white flex items-center justify-center text-sm font-semibold shadow-sm">
                      {getInitials(user.full_name)}
                    </div>
                  </Link>
                  <div>
                    <Link to={`/researchers/${user.id}`} className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] block">
                      {user.full_name}
                    </Link>
                    <div className="text-xs text-[#697386] capitalize">
                      {user.role} · {user.department_name || user.department_code || 'Chanakya University'}
                    </div>
                  </div>

                  <div className="pt-2.5 border-t border-[#F0ECE2] space-y-1 text-xs">
                    <Link to="/library" className="flex items-center justify-between py-1 text-[#3B485C] hover:text-[#142B4A]">
                      <span className="inline-flex items-center gap-2"><BookMarked className="h-3.5 w-3.5 text-[#8E6914]" /> Saved papers</span>
                      <span className="font-semibold text-[#142B4A]">{user.saved_papers_count || 0}</span>
                    </Link>
                    <Link to="/collections" className="flex items-center justify-between py-1 text-[#3B485C] hover:text-[#142B4A]">
                      <span className="inline-flex items-center gap-2"><FolderOpen className="h-3.5 w-3.5 text-[#697386]" /> Collections</span>
                      <span className="font-semibold text-[#142B4A]">{collectionsCount}</span>
                    </Link>
                    <Link to="/researchers" className="flex items-center justify-between py-1 text-[#3B485C] hover:text-[#142B4A]">
                      <span className="inline-flex items-center gap-2"><Users className="h-3.5 w-3.5 text-[#697386]" /> Following</span>
                      <span className="font-semibold text-[#142B4A]">{user.following_count || 0}</span>
                    </Link>
                  </div>
                </div>
              </div>

              <div className="surface-card p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide">Areas of Interest</h2>
                  <Link to="/settings" className="text-[11px] text-[#8E6914] font-medium hover:underline">Edit</Link>
                </div>
                {(user.research_tags || []).length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {user.research_tags.map((t) => (
                      <Link key={t} to={`/search?q=${encodeURIComponent(t.replace(/-/g, ' '))}`} className="topic-pill">
                        {formatTopicLabel(t)}
                      </Link>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[#697386]">
                    Add your topics in <Link to="/settings" className="text-[#142B4A] underline">Settings</Link>.
                  </p>
                )}
              </div>

              {recentlyViewed.length > 0 && (
                <div className="surface-card p-4 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide flex items-center gap-1.5">
                      <Clock className="h-3.5 w-3.5 text-[#697386]" /> Recently Viewed
                    </h2>
                    <Link to="/library?tab=recent" className="text-[11px] text-[#8E6914] hover:underline">All</Link>
                  </div>
                  <div className="divide-y divide-[#F3F0E8]">
                    {recentlyViewed.map((p) => (
                      <Link
                        key={p.id}
                        to={`/papers/${p.id}`}
                        className="block py-2 first:pt-0 text-xs text-[#263247] hover:text-[#8E6914] line-clamp-2 leading-snug"
                      >
                        {p.title}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="surface-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-[#142B4A]">Join the campus community</h2>
              <p className="text-xs text-[#697386] leading-relaxed">
                Sign in to share ideas, bookmark papers and posts, and connect with Chanakya University researchers.
              </p>
              <div className="flex flex-col gap-2">
                <Link to="/login" className="btn-primary text-xs w-full">Sign In</Link>
                <Link to="/register" className="btn-secondary text-xs w-full">Create Profile</Link>
              </div>
            </div>
          )}
        </aside>

        {/* CENTER COLUMN: Community Feed (Main Focus) */}
        <section className="lg:col-span-6 space-y-4 min-w-0">
          {/* Warm Post Composer */}
          {user && (
            <div className="surface-card p-4">
              {!composerOpen ? (
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-full bg-[#142B4A] text-[#FBF5E4] flex items-center justify-center text-xs font-semibold shrink-0">
                    {getInitials(user.full_name)}
                  </div>
                  <button
                    onClick={() => setComposerOpen(true)}
                    className="flex-1 text-left rounded-full border border-[#DCD7CA] bg-[#FAF8F2] hover:bg-[#F3F4F2] px-4 py-2 text-sm text-[#697386] transition-colors"
                  >
                    What&apos;s something interesting you&apos;re working on?
                  </button>
                  <Link to="/discussions/new" className="btn-secondary text-xs py-2 hidden sm:inline-flex">
                    <PenSquare className="h-3.5 w-3.5" /> Attach Paper
                  </Link>
                </div>
              ) : (
                <form onSubmit={handlePublish} className="space-y-3">
                  <input
                    required
                    value={postTitle}
                    onChange={(e) => setPostTitle(e.target.value)}
                    placeholder="Give your idea, question, or update a headline..."
                    className="input-field font-medium"
                  />
                  <textarea
                    required
                    rows={3}
                    value={postContent}
                    onChange={(e) => setPostContent(e.target.value)}
                    placeholder="What's something interesting you're working on?"
                    className="input-field"
                  />
                  <input
                    value={postTags}
                    onChange={(e) => setPostTags(e.target.value)}
                    placeholder="Topics (e.g. Machine Learning, Clean Energy, Bioinformatics)"
                    className="input-field text-xs"
                  />
                  <div className="flex items-center justify-between pt-1">
                    <Link to="/discussions/new" className="text-xs text-[#8E6914] font-medium hover:underline">
                      Attach a research paper →
                    </Link>
                    <div className="flex gap-2">
                      <button type="button" onClick={() => setComposerOpen(false)} className="btn-secondary text-xs py-1.5">
                        Cancel
                      </button>
                      <button type="submit" disabled={posting} className="btn-primary text-xs py-1.5">
                        {posting ? 'Sharing...' : 'Share Post'}
                      </button>
                    </div>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Feed Tabs */}
          <div className="flex items-center justify-between border-b border-[#E6E2D8]">
            <div className="flex items-center gap-1 overflow-x-auto">
              {[
                ...(user ? [{ id: 'personalized', label: 'For You' }, { id: 'following', label: 'Following' }] : []),
                { id: 'all', label: 'Recent' },
                ...(user ? [{ id: 'saved', label: 'Saved Posts' }] : []),
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setFeedMode(tab.id as any)}
                  className={`px-3.5 py-2.5 text-xs font-semibold border-b-2 whitespace-nowrap transition-colors ${
                    feedMode === tab.id
                      ? 'border-[#D6AA35] text-[#142B4A]'
                      : 'border-transparent text-[#697386] hover:text-[#142B4A]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Community Posts */}
          {feedLoading ? (
            <CardSkeleton rows={3} />
          ) : posts.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title={feedMode === 'saved' ? 'No saved posts yet' : 'No community posts here yet'}
              description={
                feedMode === 'saved'
                  ? 'Bookmark posts from the community feed to revisit them anytime.'
                  : 'Follow fellow students and faculty to see their updates here.'
              }
              action={<Link to="/discussions" className="btn-primary text-xs">Explore All Discussions</Link>}
            />
          ) : (
            <div className="space-y-4">
              {posts.map((post, idx) => (
                <React.Fragment key={post.id}>
                  <article className="surface-card p-5 space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <Link
                          to={`/researchers/${post.author?.id}`}
                          className="h-9 w-9 rounded-full bg-[#E9EFE8] text-[#142B4A] flex items-center justify-center text-xs font-semibold shrink-0"
                        >
                          {getInitials(post.author?.full_name)}
                        </Link>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <Link
                              to={`/researchers/${post.author?.id}`}
                              className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] truncate"
                            >
                              {post.author?.full_name}
                            </Link>
                            {post.is_synthetic && (
                              <span className="text-[10px] rounded-full bg-[#F3F4F2] text-[#697386] px-2 py-0.5 shrink-0">
                                Sample
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-[#697386] capitalize truncate">
                            {post.author?.role} · {post.author?.department_code} · {formatRelativeDate(post.created_at)}
                          </div>
                        </div>
                      </div>

                      {(user?.id === post.author?.id || user?.role === 'admin') && (
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            onClick={() => {
                              setEditingPost(post);
                              setEditTitle(post.title);
                              setEditContent(post.content);
                            }}
                            className="p-1 text-[#8A92A0] hover:text-[#142B4A]"
                            title="Edit post"
                          >
                            <Edit2 className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => setDeleteTargetId(post.id)}
                            className="p-1 text-[#8A92A0] hover:text-rose-600"
                            title="Delete post"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <Link
                        to={`/discussions?post=${post.id}`}
                        className="text-[15px] font-semibold text-[#142B4A] hover:text-[#8E6914] leading-snug block"
                      >
                        {post.title}
                      </Link>
                      <p className="text-[13.5px] text-[#3B485C] leading-relaxed line-clamp-3">
                        {post.content}
                      </p>
                    </div>

                    {post.attached_paper && (
                      <Link
                        to={`/papers/${post.attached_paper.id}`}
                        className="flex items-start gap-2.5 rounded-lg border border-[#E6E2D8] bg-[#FAF8F2] hover:border-[#D6AA35] p-3 transition-colors"
                      >
                        <BookOpen className="h-4 w-4 text-[#8E6914] shrink-0 mt-0.5" />
                        <div className="min-w-0">
                          <div className="text-xs font-semibold text-[#142B4A] line-clamp-1">
                            {post.attached_paper.title}
                          </div>
                          <div className="text-[11px] text-[#697386]">
                            {(post.attached_paper.authors || []).slice(0, 2).join(', ')}
                            {post.attached_paper.publication_year ? ` · ${post.attached_paper.publication_year}` : ''}
                          </div>
                        </div>
                      </Link>
                    )}

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-[#F0ECE2]">
                      <div className="flex flex-wrap gap-1.5">
                        {(post.tags || []).slice(0, 3).map((t: string) => (
                          <Link
                            key={t}
                            to={`/search?q=${encodeURIComponent(t.replace(/-/g, ' '))}`}
                            className="topic-pill"
                          >
                            {formatTopicLabel(t)}
                          </Link>
                        ))}
                      </div>

                      <div className="flex items-center gap-2 text-xs text-[#697386]">
                        <button
                          onClick={() => handleLike(post.id)}
                          className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 font-medium transition-colors ${
                            post.has_upvoted
                              ? 'bg-[#FBF5E4] text-[#8E6914]'
                              : 'hover:bg-[#F3F4F2] text-[#697386]'
                          }`}
                        >
                          <Heart className={`h-3.5 w-3.5 ${post.has_upvoted ? 'fill-[#D6AA35] text-[#D6AA35]' : ''}`} />
                          <span>{post.upvote_count}</span>
                        </button>
                        <Link
                          to={`/discussions?post=${post.id}`}
                          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1 hover:bg-[#F3F4F2] text-[#697386]"
                        >
                          <MessageSquare className="h-3.5 w-3.5" />
                          <span>{post.comment_count}</span>
                        </Link>
                        {user && (
                          <button
                            onClick={() => handleSavePost(post.id)}
                            className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 font-medium transition-colors ${
                              post.is_saved_by_me
                                ? 'bg-[#E9EFE8] text-[#2E5438]'
                                : 'hover:bg-[#F3F4F2] text-[#697386]'
                            }`}
                            title={post.is_saved_by_me ? 'Saved' : 'Save post'}
                          >
                            {post.is_saved_by_me ? (
                              <BookmarkCheck className="h-3.5 w-3.5" />
                            ) : (
                              <Bookmark className="h-3.5 w-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </div>
                  </article>

                  {/* Interleave a single recommended publication smoothly */}
                  {idx === 1 && recPapers.length > 0 && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-semibold text-[#697386] uppercase tracking-wide">
                          Suggested reading for you
                        </span>
                        <Link to="/recommendations" className="text-xs font-medium text-[#8E6914] hover:underline">
                          View all
                        </Link>
                      </div>
                      <PaperCard paper={recPapers[0]} />
                    </div>
                  )}
                </React.Fragment>
              ))}
            </div>
          )}
        </section>

        {/* RIGHT SIDEBAR: Campus Highlight, People to Connect With, Topics, Reading */}
        <aside className="lg:col-span-3 space-y-4">
          {/* Selective Campus Learning Highlight Card */}
          <Link to="/discover" className="surface-card-interactive overflow-hidden block">
            <img
              src="/images/chanakya/Workshop5.jpg"
              alt="Chanakya University seminar workshop"
              className="h-28 w-full object-cover"
            />
            <div className="p-3.5 space-y-1">
              <div className="text-[11px] font-semibold text-[#8E6914]">Campus Research Spotlight</div>
              <div className="text-xs font-semibold text-[#142B4A] leading-snug">
                Explore seminar readings & faculty work across all six departments
              </div>
            </div>
          </Link>

          {/* People to Connect With */}
          <div className="surface-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide">
                People to Connect With
              </h2>
              <Link to="/researchers" className="text-[11px] text-[#8E6914] hover:underline">Directory</Link>
            </div>
            <div className="space-y-3">
              {recResearchers.slice(0, 4).map((r) => (
                <div key={r.id} className="flex items-start justify-between gap-2.5">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="h-8 w-8 rounded-full bg-[#E9EFE8] text-[#142B4A] flex items-center justify-center text-[11px] font-semibold shrink-0 mt-0.5">
                      {getInitials(r.full_name)}
                    </div>
                    <div className="min-w-0">
                      <Link
                        to={`/researchers/${r.id}`}
                        className="text-xs font-semibold text-[#142B4A] hover:text-[#8E6914] truncate block"
                      >
                        {r.full_name}
                      </Link>
                      <div className="text-[11px] text-[#697386] truncate capitalize">
                        {r.role} · {r.department_code}
                      </div>
                    </div>
                  </div>
                  {user && (
                    <button
                      onClick={() => handleFollow(r.id, r.full_name)}
                      disabled={followedMap[r.id]}
                      className={`shrink-0 rounded-lg px-2 py-1 text-[11px] font-medium border transition-colors ${
                        followedMap[r.id]
                          ? 'bg-[#E9EFE8] border-[#CFE0CC] text-[#2E5438]'
                          : 'bg-white border-[#DCD7CA] text-[#142B4A] hover:bg-[#FAF8F2]'
                      }`}
                    >
                      {followedMap[r.id] ? <UserCheck className="h-3.5 w-3.5" /> : <UserPlus className="h-3.5 w-3.5" />}
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Topics People Are Exploring */}
          <div className="surface-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide flex items-center gap-1.5">
                <TrendingUp className="h-3.5 w-3.5 text-[#8E6914]" /> Topics on Campus
              </h2>
              <Link to="/trends" className="text-[11px] text-[#8E6914] hover:underline">Trends</Link>
            </div>
            <div className="space-y-1.5">
              {trends.slice(0, 5).map((t) => (
                <Link
                  key={t.topic}
                  to={`/search?q=${encodeURIComponent(t.topic.replace(/-/g, ' '))}`}
                  className="block rounded-lg px-2.5 py-2 hover:bg-[#FAF8F2] transition-colors"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-medium text-[#142B4A] truncate">
                      {formatTopicLabel(t.topic)}
                    </span>
                    {t.is_spike && <span className="gold-badge shrink-0">Rising</span>}
                  </div>
                  <div className="text-[11px] text-[#697386] mt-0.5">
                    {t.recent_count} recent discussions & reads
                  </div>
                </Link>
              ))}
            </div>
          </div>

          {recPapers.length > 1 && (
            <div className="surface-card p-4 space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide">Recommended Reading</h2>
                <Link to={user ? '/recommendations' : '/discover'} className="text-[11px] text-[#8E6914] hover:underline inline-flex items-center gap-0.5">
                  More <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
              <div className="divide-y divide-[#F3F0E8]">
                {recPapers.slice(1, 4).map((p) => (
                  <Link key={p.id} to={`/papers/${p.id}`} className="block py-2.5 first:pt-0 group">
                    <div className="text-xs font-medium text-[#142B4A] group-hover:text-[#8E6914] line-clamp-2 leading-snug">
                      {p.title}
                    </div>
                    <div className="text-[11px] text-[#697386] mt-0.5">
                      {p.publication_year || 'Recent'} · {p.save_count > 0 ? `Saved by ${p.save_count}` : `${p.citation_count} citations`}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>
      </div>

      {/* Edit Post Modal */}
      {editingPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/45 p-4">
          <form onSubmit={handleSaveEdit} className="surface-card max-w-lg w-full p-6 space-y-4 shadow-dropdown">
            <h3 className="text-base font-semibold text-[#142B4A]">Edit Post</h3>
            <input
              required
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="input-field font-medium"
            />
            <textarea
              required
              rows={5}
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="input-field"
            />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setEditingPost(null)} className="btn-secondary text-xs">
                Cancel
              </button>
              <button type="submit" className="btn-primary text-xs">
                Save Changes
              </button>
            </div>
          </form>
        </div>
      )}

      <ConfirmDialog
        open={deleteTargetId !== null}
        title="Delete post?"
        message="This will permanently delete this post and all its replies."
        confirmLabel="Delete"
        danger
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />
    </div>
  );
}
