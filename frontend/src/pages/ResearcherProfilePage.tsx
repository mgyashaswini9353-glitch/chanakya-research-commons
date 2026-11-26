import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  BookOpen,
  ExternalLink,
  Globe,
  MessageSquare,
  UserCheck,
  UserPlus,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import {
  CardSkeleton,
  EmptyState,
  formatRelativeDate,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

export default function ResearcherProfilePage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { showToast } = useToast();
  const [profile, setProfile] = useState<any>(null);
  const [tab, setTab] = useState<'overview' | 'library' | 'discussions'>('overview');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .get(`/api/users/${id}`)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [id]);

  const toggleFollow = async () => {
    if (!user || !profile) return;
    if (profile.is_following) {
      await api.del(`/api/users/${profile.id}/follow`);
      showToast(`Unfollowed ${profile.full_name}`, 'info');
    } else {
      await api.post(`/api/users/${profile.id}/follow`);
      showToast(`Now following ${profile.full_name}`);
    }
    setProfile({
      ...profile,
      is_following: !profile.is_following,
      followers_count: (profile.followers_count || 0) + (profile.is_following ? -1 : 1),
    });
  };

  if (loading) return <CardSkeleton rows={3} />;
  if (!profile) {
    return (
      <div className="surface-card p-10 text-center text-sm text-[#697386]">
        Member profile not found.
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <Link to="/researchers" className="inline-flex items-center gap-1.5 text-xs font-medium text-[#697386] hover:text-[#142B4A]">
        <ArrowLeft className="h-3.5 w-3.5" /> Back to People Directory
      </Link>

      {/* Warm Academic Profile Card */}
      <div className="surface-card overflow-hidden">
        <div className="h-32 relative overflow-hidden">
          <img
            src="/images/chanakya/CampusArch.jpg"
            alt="Chanakya University Architecture"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-[#142B4A]/70" />
          <div className="absolute bottom-0 inset-x-0 h-1 bg-[#D6AA35]" />
        </div>

        <div className="px-6 pb-6 -mt-10 space-y-4 relative">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div className="flex items-end gap-4">
              <div className="h-20 w-20 rounded-full bg-[#142B4A] text-[#FBF5E4] border-4 border-white flex items-center justify-center text-xl font-semibold shadow-sm shrink-0">
                {getInitials(profile.full_name)}
              </div>
              <div className="pt-12">
                <h1 className="text-2xl font-semibold text-[#142B4A] leading-tight">{profile.full_name}</h1>
                <div className="text-sm text-[#697386] capitalize mt-0.5">
                  {profile.role} · {profile.department_name || profile.department_code || 'Chanakya University'}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {user && user.id !== profile.id && (
                <button onClick={toggleFollow} className={profile.is_following ? 'btn-secondary text-xs' : 'btn-primary text-xs'}>
                  {profile.is_following ? <UserCheck className="h-4 w-4 text-[#2E5438]" /> : <UserPlus className="h-4 w-4" />}
                  {profile.is_following ? 'Following' : 'Connect & Follow'}
                </button>
              )}
              {user && user.id === profile.id && (
                <Link to="/settings" className="btn-secondary text-xs">Edit Profile</Link>
              )}
            </div>
          </div>

          {profile.bio && (
            <p className="text-sm text-[#263247] leading-relaxed max-w-3xl">{profile.bio}</p>
          )}

          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-[#697386] pt-1">
            <span><strong className="text-[#142B4A]">{profile.followers_count || 0}</strong> followers</span>
            <span><strong className="text-[#142B4A]">{profile.following_count || 0}</strong> following</span>
            <span><strong className="text-[#142B4A]">{profile.saved_papers_count || 0}</strong> saved papers</span>
            <span><strong className="text-[#142B4A]">{profile.posts_count || 0}</strong> discussions</span>
            {profile.personal_website && (
              <a href={profile.personal_website} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-[#8E6914] font-medium hover:underline">
                <Globe className="h-3.5 w-3.5" /> Personal page <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        <div className="border-t border-[#E6E2D8] px-6 flex items-center gap-2 bg-[#FAF8F2]/50">
          {[
            { id: 'overview', label: 'About & Interests' },
            { id: 'library', label: `Reading & Publications (${(profile.recent_saved_papers || []).length})` },
            { id: 'discussions', label: `Contributions (${(profile.recent_posts || []).length})` },
          ].map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`px-3.5 py-3 text-xs font-semibold border-b-2 transition-colors ${
                tab === t.id ? 'border-[#D6AA35] text-[#142B4A]' : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {tab === 'overview' && (
        <div className="grid md:grid-cols-2 gap-6">
          <div className="surface-card p-6 space-y-4">
            <h2 className="text-sm font-semibold text-[#142B4A]">Areas & Research Interests</h2>
            <p className="text-sm text-[#3B485C] leading-relaxed">
              {profile.research_interests_text || 'Exploring interdisciplinary research across Chanakya University.'}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(profile.research_tags || []).map((t: string) => (
                <Link key={t} to={`/search?q=${encodeURIComponent(t.replace(/-/g, ' '))}`} className="topic-pill">
                  {formatTopicLabel(t)}
                </Link>
              ))}
            </div>
          </div>

          <div className="surface-card p-6 space-y-4">
            <h2 className="text-sm font-semibold text-[#142B4A]">Publications & Academic Links</h2>
            {(profile.publication_links || []).length === 0 ? (
              <p className="text-xs text-[#697386]">No external publication links shared yet.</p>
            ) : (
              <div className="space-y-2">
                {profile.publication_links.map((link: string, idx: number) => (
                  <a
                    key={idx}
                    href={link}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between rounded-lg border border-[#E6E2D8] px-3.5 py-2.5 text-xs text-[#142B4A] hover:border-[#D6AA35]"
                  >
                    <span className="truncate">{link}</span>
                    <ExternalLink className="h-3.5 w-3.5 text-[#8E6914] shrink-0 ml-2" />
                  </a>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === 'library' && (
        <div className="space-y-3">
          {(profile.recent_saved_papers || []).length === 0 ? (
            <EmptyState icon={BookOpen} title="No saved publications yet" description="This member has not saved any papers yet." />
          ) : (
            profile.recent_saved_papers.map((p: any) => (
              <Link key={p.id} to={`/papers/${p.id}`} className="surface-card-interactive p-5 block space-y-1">
                <div className="text-sm font-semibold text-[#142B4A]">{p.title}</div>
                <div className="text-xs text-[#697386]">
                  {p.venue || 'Publication'} {p.publication_year ? `· ${p.publication_year}` : ''} · Saved by {p.save_count} members
                </div>
              </Link>
            ))
          )}
        </div>
      )}

      {tab === 'discussions' && (
        <div className="space-y-3">
          {(profile.recent_posts || []).length === 0 ? (
            <EmptyState icon={MessageSquare} title="No community posts yet" description="This member has not shared any discussions yet." />
          ) : (
            profile.recent_posts.map((po: any) => (
              <Link key={po.id} to={`/discussions?post=${po.id}`} className="surface-card-interactive p-5 block space-y-1.5">
                <div className="text-sm font-semibold text-[#142B4A]">{po.title}</div>
                <div className="text-xs text-[#697386]">
                  {formatRelativeDate(po.created_at)} · {po.upvote_count} likes · {po.comment_count} replies
                </div>
              </Link>
            ))
          )}
        </div>
      )}
    </div>
  );
}
