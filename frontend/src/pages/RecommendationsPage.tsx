import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, MessageSquare, UserCheck, UserPlus, Users } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';
import PaperCard from '../components/PaperCard';
import {
  CardSkeleton,
  EmptyState,
  formatRelativeDate,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

export default function RecommendationsPage() {
  const { showToast } = useToast();
  const [paperRecs, setPaperRecs] = useState<any[]>([]);
  const [userRecs, setUserRecs] = useState<any[]>([]);
  const [discussions, setDiscussions] = useState<any[]>([]);
  const [followed, setFollowed] = useState<Record<number, boolean>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/api/recommendations/papers?limit=10').catch(() => ({ recommendations: [] })),
      api.get('/api/recommendations/researchers?limit=8').catch(() => ({ recommendations: [] })),
      api.get('/api/posts?feed=personalized&limit=4').catch(() => ({ items: [] })),
    ])
      .then(([pr, ur, po]) => {
        setPaperRecs(pr.recommendations || []);
        setUserRecs(ur.recommendations || []);
        setDiscussions(po.items || []);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleFollow = async (uid: number, name: string) => {
    try {
      await api.post(`/api/users/${uid}/follow`);
      setFollowed((prev) => ({ ...prev, [uid]: true }));
      showToast(`Now following ${name}`);
    } catch (err: any) {
      showToast(err.message || 'Could not follow member', 'error');
    }
  };

  if (loading) return <CardSkeleton rows={4} />;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Recommended for You</h1>
        <p className="text-sm text-[#697386] mt-0.5">
          Publications, colleagues, and discussions tailored to your research interests and reading library.
        </p>
      </div>

      {/* Recommended Publications */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-[#142B4A] flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-[#8E6914]" /> Publications You May Want to Read
          </h2>
          <Link to="/discover" className="text-xs font-medium text-[#8E6914] hover:underline">
            Browse all research
          </Link>
        </div>

        {paperRecs.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="Start saving papers to refine recommendations"
            description="Add a few topics in Settings or save papers to your library to personalize this feed."
            action={<Link to="/discover" className="btn-primary text-xs">Explore Research</Link>}
          />
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {paperRecs.map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        )}
      </section>

      {/* Researchers You May Know */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-[#142B4A] flex items-center gap-2">
            <Users className="h-4 w-4 text-[#142B4A]" /> Researchers with Shared Interests
          </h2>
          <Link to="/researchers" className="text-xs font-medium text-[#8E6914] hover:underline">
            View full directory
          </Link>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {userRecs.map((r) => (
            <div key={r.id} className="surface-card-interactive p-4 flex flex-col justify-between gap-3">
              <div className="space-y-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="h-9 w-9 rounded-full bg-[#142B4A] text-white flex items-center justify-center text-xs font-semibold shrink-0">
                    {getInitials(r.full_name)}
                  </div>
                  <div className="min-w-0">
                    <Link
                      to={`/researchers/${r.id}`}
                      className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] truncate block"
                    >
                      {r.full_name}
                    </Link>
                    <div className="text-[11px] text-[#697386] capitalize truncate">
                      {r.role} · {r.department_code}
                    </div>
                  </div>
                </div>

                {r.reasons?.[0] && (
                  <p className="text-xs text-[#2E5438] bg-[#E9EFE8] rounded-md px-2.5 py-1.5 leading-snug">
                    {r.reasons[0]}
                  </p>
                )}

                <div className="flex flex-wrap gap-1">
                  {(r.research_tags || []).slice(0, 3).map((t: string) => (
                    <span key={t} className="topic-pill">{formatTopicLabel(t)}</span>
                  ))}
                </div>
              </div>

              <button
                onClick={() => handleFollow(r.id, r.full_name)}
                disabled={followed[r.id]}
                className={followed[r.id] ? 'btn-secondary w-full text-xs py-1.5 text-[#2E5438]' : 'btn-primary w-full text-xs py-1.5'}
              >
                {followed[r.id] ? (
                  <><UserCheck className="h-3.5 w-3.5 text-[#8E6914]" /> Following</>
                ) : (
                  <><UserPlus className="h-3.5 w-3.5" /> Follow</>
                )}
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* Related Discussions */}
      {discussions.length > 0 && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-[#142B4A] flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-[#142B4A]" /> Discussions in Your Areas
            </h2>
            <Link to="/discussions" className="text-xs font-medium text-[#8E6914] hover:underline">
              Explore community
            </Link>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {discussions.map((d) => (
              <Link key={d.id} to={`/discussions?post=${d.id}`} className="surface-card-interactive p-5 space-y-1.5">
                <div className="text-sm font-semibold text-[#142B4A]">{d.title}</div>
                <p className="text-xs text-[#4A5568] line-clamp-2">{d.content}</p>
                <div className="text-[11px] text-[#697386] pt-1">
                  {d.author?.full_name} · {formatRelativeDate(d.created_at)} · {d.comment_count} replies
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
