import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Bookmark,
  BookmarkCheck,
  BookOpen,
  CornerDownRight,
  Edit2,
  Heart,
  MessageSquare,
  PenSquare,
  Send,
  Trash2,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  CardSkeleton,
  ConfirmDialog,
  EmptyState,
  formatRelativeDate,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

export default function DiscussionsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [searchParams] = useSearchParams();

  const [feed, setFeed] = useState<'personalized' | 'all' | 'following' | 'topics' | 'saved'>(
    user ? 'personalized' : 'all'
  );
  const [posts, setPosts] = useState<any[]>([]);
  const [selectedPost, setSelectedPost] = useState<any>(null);
  const [commentText, setCommentText] = useState('');
  const [replyToId, setReplyToId] = useState<number | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [editingPost, setEditingPost] = useState<any>(null);
  const [editTitle, setEditTitle] = useState('');
  const [editContent, setEditContent] = useState('');
  const [loading, setLoading] = useState(true);

  const loadFeed = async (f = feed) => {
    setLoading(true);
    try {
      const res = await api.get(`/api/posts?feed=${f}&limit=30`);
      setPosts(res.items || []);
    } finally {
      setLoading(false);
    }
  };

  const openPost = async (postId: number) => {
    const det = await api.get(`/api/posts/${postId}`);
    setSelectedPost(det);
    setReplyToId(null);
  };

  useEffect(() => {
    loadFeed(feed);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [feed]);

  useEffect(() => {
    const pid = searchParams.get('post');
    if (pid) openPost(Number(pid));
  }, [searchParams]);

  const toggleLike = async (postId: number) => {
    if (!user) return;
    const res = await api.post(`/api/posts/${postId}/upvote`);
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, has_upvoted: res.upvoted, upvote_count: res.upvote_count } : p))
    );
    if (selectedPost?.id === postId) {
      setSelectedPost({ ...selectedPost, has_upvoted: res.upvoted, upvote_count: res.upvote_count });
    }
  };

  const toggleSavePost = async (postId: number) => {
    if (!user) return;
    const res = await api.post(`/api/posts/${postId}/save`);
    setPosts((prev) =>
      prev.map((p) => (p.id === postId ? { ...p, is_saved_by_me: res.saved } : p))
    );
    if (selectedPost?.id === postId) {
      setSelectedPost({ ...selectedPost, is_saved_by_me: res.saved });
    }
    showToast(res.saved ? 'Post saved to My Library' : 'Removed from saved posts', res.saved ? 'success' : 'info');
    if (feed === 'saved' && !res.saved) loadFeed('saved');
  };

  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user || !selectedPost || !commentText.trim()) return;
    await api.post(`/api/posts/${selectedPost.id}/comments`, {
      content: commentText.trim(),
      parent_comment_id: replyToId,
    });
    setCommentText('');
    setReplyToId(null);
    showToast(replyToId ? 'Reply added' : 'Comment added');
    openPost(selectedPost.id);
    loadFeed(feed);
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPost) return;
    await api.patch(`/api/posts/${editingPost.id}`, {
      title: editTitle.trim(),
      content: editContent.trim(),
    });
    const editedId = editingPost.id;
    setEditingPost(null);
    showToast('Discussion updated');
    if (selectedPost?.id === editedId) openPost(editedId);
    loadFeed(feed);
  };

  const confirmDelete = async () => {
    if (!deleteTargetId) return;
    await api.del(`/api/posts/${deleteTargetId}`);
    if (selectedPost?.id === deleteTargetId) setSelectedPost(null);
    setDeleteTargetId(null);
    showToast('Discussion removed', 'info');
    loadFeed(feed);
  };

  const feedTabs = [
    ...(user
      ? [
          { id: 'personalized', label: 'For You' },
          { id: 'following', label: 'Following' },
          { id: 'topics', label: 'My Topics' },
          { id: 'saved', label: 'Saved Posts' },
        ]
      : []),
    { id: 'all', label: 'All Community' },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Chanakya Community</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Share ideas, ask questions, discuss papers, and collaborate with students and faculty across campus.
          </p>
        </div>
        {user && (
          <Link to="/discussions/new" className="btn-primary text-xs">
            <PenSquare className="h-3.5 w-3.5" /> Share an Idea or Update
          </Link>
        )}
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[#E6E2D8]">
        {feedTabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setFeed(t.id as any)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
              feed === t.id
                ? 'border-[#D6AA35] text-[#142B4A]'
                : 'border-transparent text-[#697386] hover:text-[#142B4A]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid lg:grid-cols-12 gap-6 items-start">
        {/* Post List */}
        <div className="lg:col-span-7 space-y-3.5 min-w-0">
          {loading ? (
            <CardSkeleton rows={4} />
          ) : posts.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title={feed === 'saved' ? 'No saved posts yet' : 'No discussions found'}
              description="Follow members or share a new post to start a conversation."
            />
          ) : (
            posts.map((p) => (
              <article
                key={p.id}
                onClick={() => openPost(p.id)}
                className={`surface-card-interactive p-5 space-y-3 cursor-pointer ${
                  selectedPost?.id === p.id ? 'border-[#D6AA35] ring-1 ring-[#D6AA35]/35' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="h-8 w-8 rounded-full bg-[#E9EFE8] text-[#142B4A] flex items-center justify-center text-xs font-semibold shrink-0">
                      {getInitials(p.author?.full_name)}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <Link
                          to={`/researchers/${p.author?.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-semibold text-[#142B4A] hover:text-[#8E6914] truncate"
                        >
                          {p.author?.full_name}
                        </Link>
                        {p.is_synthetic && (
                          <span className="text-[10px] rounded-full bg-[#F3F4F2] text-[#697386] px-2 py-0.5 shrink-0">
                            Sample
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-[#697386] capitalize truncate">
                        {p.author?.role} · {p.author?.department_code} · {formatRelativeDate(p.created_at)}
                      </div>
                    </div>
                  </div>
                  {(user?.id === p.author?.id || user?.role === 'admin') && (
                    <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => {
                          setEditingPost(p);
                          setEditTitle(p.title);
                          setEditContent(p.content);
                        }}
                        className="text-[#8A92A0] hover:text-[#142B4A] p-1"
                        title="Edit post"
                      >
                        <Edit2 className="h-3.5 w-3.5" />
                      </button>
                      <button
                        onClick={() => setDeleteTargetId(p.id)}
                        className="text-[#8A92A0] hover:text-rose-600 p-1"
                        title="Delete post"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>

                <h2 className="text-[15px] font-semibold text-[#142B4A] leading-snug">{p.title}</h2>
                <p className="text-[13.5px] text-[#3B485C] leading-relaxed line-clamp-3">{p.content}</p>

                {p.attached_paper && (
                  <Link
                    to={`/papers/${p.attached_paper.id}`}
                    onClick={(e) => e.stopPropagation()}
                    className="flex items-center gap-2 rounded-lg border border-[#E6E2D8] bg-[#FAF8F2] px-3 py-2 text-xs text-[#142B4A] hover:border-[#D6AA35]"
                  >
                    <BookOpen className="h-3.5 w-3.5 text-[#8E6914] shrink-0" />
                    <span className="font-medium truncate">{p.attached_paper.title}</span>
                  </Link>
                )}

                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-[#F0ECE2]">
                  <div className="flex flex-wrap gap-1.5">
                    {(p.tags || []).slice(0, 3).map((t: string) => (
                      <span key={t} className="topic-pill">{formatTopicLabel(t)}</span>
                    ))}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-[#697386]">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleLike(p.id);
                      }}
                      className={`inline-flex items-center gap-1 rounded-lg px-2 py-1 font-medium ${
                        p.has_upvoted ? 'bg-[#FBF5E4] text-[#8E6914]' : 'hover:bg-[#F3F4F2]'
                      }`}
                    >
                      <Heart className={`h-3.5 w-3.5 ${p.has_upvoted ? 'fill-[#D6AA35] text-[#D6AA35]' : ''}`} />
                      {p.upvote_count}
                    </button>
                    <span className="inline-flex items-center gap-1 px-1.5">
                      <MessageSquare className="h-3.5 w-3.5" /> {p.comment_count}
                    </span>
                    {user && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleSavePost(p.id);
                        }}
                        className={`inline-flex items-center rounded-lg px-2 py-1 ${
                          p.is_saved_by_me ? 'bg-[#E9EFE8] text-[#2E5438]' : 'hover:bg-[#F3F4F2]'
                        }`}
                        title={p.is_saved_by_me ? 'Saved' : 'Save post'}
                      >
                        {p.is_saved_by_me ? <BookmarkCheck className="h-3.5 w-3.5" /> : <Bookmark className="h-3.5 w-3.5" />}
                      </button>
                    )}
                  </div>
                </div>
              </article>
            ))
          )}
        </div>

        {/* Thread Detail Column */}
        <aside className="lg:col-span-5 min-w-0">
          {selectedPost ? (
            <div className="surface-card p-5 sticky top-20 space-y-4 max-h-[80vh] overflow-y-auto">
              <div className="space-y-2">
                <h2 className="text-base font-semibold text-[#142B4A] leading-snug">{selectedPost.title}</h2>
                <div className="text-xs text-[#697386]">
                  {selectedPost.author?.full_name} · {selectedPost.author?.department_code} · {formatRelativeDate(selectedPost.created_at)}
                </div>
                <p className="text-sm text-[#263247] leading-relaxed whitespace-pre-line pt-1">
                  {selectedPost.content}
                </p>
              </div>

              <div className="border-t border-[#E6E2D8] pt-4 space-y-3">
                <div className="text-xs font-semibold text-[#142B4A]">
                  Replies ({(selectedPost.comments || []).length})
                </div>

                <div className="space-y-2.5">
                  {(selectedPost.comments || []).map((c: any) => (
                    <div
                      key={c.id}
                      className={`rounded-lg p-3 text-xs border ${
                        c.parent_comment_id
                          ? 'ml-5 bg-[#E9EFE8]/45 border-[#D7E3D5]'
                          : 'bg-[#FAF8F2] border-[#E6E2D8]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] text-[#697386] mb-1">
                        <span className="font-semibold text-[#142B4A] inline-flex items-center gap-1">
                          {c.parent_comment_id && <CornerDownRight className="h-3 w-3 text-[#8E6914]" />}
                          {c.author_name} ({c.department_code})
                        </span>
                        {user && !c.parent_comment_id && (
                          <button
                            onClick={() => setReplyToId(c.id)}
                            className="text-[#8E6914] font-medium hover:underline"
                          >
                            Reply
                          </button>
                        )}
                      </div>
                      <p className="text-[#263247] leading-relaxed">{c.content}</p>
                    </div>
                  ))}
                </div>

                {user ? (
                  <form onSubmit={handleAddComment} className="space-y-2 pt-2 border-t border-[#E6E2D8]">
                    {replyToId && (
                      <div className="flex items-center justify-between text-[11px] text-[#8E6914] bg-[#FBF5E4] px-2.5 py-1 rounded-md">
                        <span>Replying to comment</span>
                        <button type="button" onClick={() => setReplyToId(null)} className="underline">Cancel</button>
                      </div>
                    )}
                    <div className="flex gap-2">
                      <input
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder={replyToId ? 'Write a reply...' : 'Add a helpful comment...'}
                        className="input-field text-xs py-2"
                      />
                      <button type="submit" className="btn-primary px-3 py-2 text-xs shrink-0" aria-label="Send comment">
                        <Send className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </form>
                ) : (
                  <p className="text-xs text-[#697386]">
                    <Link to="/login" className="text-[#142B4A] font-medium underline">Sign in</Link> to join the conversation.
                  </p>
                )}
              </div>
            </div>
          ) : (
            <div className="surface-card p-10 text-center space-y-2">
              <MessageSquare className="h-7 w-7 text-[#D4CEBE] mx-auto" />
              <div className="text-sm font-medium text-[#142B4A]">Select a discussion</div>
              <p className="text-xs text-[#697386]">
                Click any post on the left to read replies and contribute your perspective.
              </p>
            </div>
          )}
        </aside>
      </div>

      {editingPost && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/45 p-4">
          <form onSubmit={handleSaveEdit} className="surface-card max-w-lg w-full p-6 space-y-4 shadow-dropdown">
            <h3 className="text-base font-semibold text-[#142B4A]">Edit Discussion</h3>
            <input required value={editTitle} onChange={(e) => setEditTitle(e.target.value)} className="input-field font-medium" />
            <textarea required rows={5} value={editContent} onChange={(e) => setEditContent(e.target.value)} className="input-field" />
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setEditingPost(null)} className="btn-secondary text-xs">Cancel</button>
              <button type="submit" className="btn-primary text-xs">Save Changes</button>
            </div>
          </form>
        </div>
      )}

      <ConfirmDialog
        open={deleteTargetId !== null}
        title="Delete discussion?"
        message="This will permanently remove the post and all replies."
        confirmLabel="Delete Post"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTargetId(null)}
      />
    </div>
  );
}
