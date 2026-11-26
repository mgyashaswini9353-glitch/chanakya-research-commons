import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Check, Plus, TrendingUp } from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { CardSkeleton, formatTopicLabel } from '../components/UIPrimitives';

const LINE_COLORS = ['#142B4A', '#8E6914', '#3B82F6', '#64748B', '#0F766E', '#475569'];

export default function TrendsPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [windowDays, setWindowDays] = useState(14);
  const [data, setData] = useState<any>(null);
  const [popularPosts, setPopularPosts] = useState<any[]>([]);
  const [followedTopics, setFollowedTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/api/trends?window_days=${windowDays}`),
      api.get('/api/posts?feed=all&limit=5').catch(() => ({ items: [] })),
      user ? api.get('/api/users/me/topics').catch(() => []) : Promise.resolve([]),
    ])
      .then(([tr, po, ft]) => {
        setData(tr);
        setPopularPosts(po.items || []);
        setFollowedTopics(ft || []);
      })
      .finally(() => setLoading(false));
  }, [windowDays, user]);

  const toggleTopic = async (topic: string) => {
    if (!user) return;
    if (followedTopics.includes(topic)) {
      await api.del(`/api/users/me/topics/follow/${encodeURIComponent(topic)}`);
      setFollowedTopics((p) => p.filter((x) => x !== topic));
      showToast(`Unfollowed ${formatTopicLabel(topic)}`, 'info');
    } else {
      await api.post('/api/users/me/topics/follow', { topic });
      setFollowedTopics((p) => [...p, topic]);
      showToast(`Following ${formatTopicLabel(topic)}`);
    }
  };

  const chartTopics = (data?.trending_topics || []).slice(0, 5).map((t: any) => t.topic);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Research Trends</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Discover emerging areas of interest, popular topics, and active discussions across the university.
          </p>
        </div>

        <div className="inline-flex rounded-md border border-[#DCD7CA] bg-white p-0.5">
          {[
            { d: 14, label: 'Past 2 Weeks' },
            { d: 30, label: 'Past Month' },
            { d: 60, label: 'Past 2 Months' },
          ].map((opt) => (
            <button
              key={opt.d}
              onClick={() => setWindowDays(opt.d)}
              className={`px-3 py-1.5 text-xs font-medium rounded transition-colors ${
                windowDays === opt.d ? 'bg-[#142B4A] text-white' : 'text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <CardSkeleton rows={3} />
      ) : (
        <>
          {/* Emerging / Fast-Growing Areas */}
          {(data?.topic_spikes || []).length > 0 && (
            <section className="space-y-3">
              <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-1.5">
                <TrendingUp className="h-4 w-4 text-[#8E6914]" /> Emerging Research Areas
              </h2>
              <div className="grid md:grid-cols-3 gap-4">
                {data.topic_spikes.map((sp: any) => (
                  <Link
                    key={sp.topic}
                    to={`/search?q=${encodeURIComponent(sp.topic.replace(/-/g, ' '))}`}
                    className="surface-card-interactive p-5 space-y-2.5 border-l-4 border-l-[#D6AA35]"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-semibold text-[#142B4A]">
                        Growing interest in {formatTopicLabel(sp.topic)}
                      </h3>
                      <ArrowUpRight className="h-4 w-4 text-[#8E6914] shrink-0" />
                    </div>
                    <p className="text-xs text-[#4A5568] leading-relaxed">
                      {sp.human_summary ||
                        `Activity reached ${sp.peak_week_count} interactions in a single week, compared to a typical average of ${Math.round(sp.baseline_weekly_mean)} per week.`}
                    </p>
                    <div className="text-[11px] text-[#697386] pt-2 border-t border-[#F0ECE2]">
                      {sp.total_count} total university reads, saves & discussions
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          )}

          {/* Research Activity Over Time Chart */}
          <section className="surface-card p-6 space-y-4">
            <div>
              <h2 className="text-base font-semibold text-[#142B4A]">Research Activity Over Time</h2>
              <p className="text-xs text-[#697386]">
                Weekly reading, saving, search, and discussion activity across leading research topics.
              </p>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data?.weekly_series || []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E6E2D8" />
                  <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#697386' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#697386' }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #E6E2D8',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Legend
                    wrapperStyle={{ fontSize: 12 }}
                    formatter={(val) => formatTopicLabel(String(val))}
                  />
                  {chartTopics.map((topic: string, idx: number) => (
                    <Line
                      key={topic}
                      type="monotone"
                      dataKey={topic}
                      name={formatTopicLabel(topic)}
                      stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* Two Columns: Popular Topics Table + Active Discussions */}
          <div className="grid lg:grid-cols-12 gap-6 items-start">
            <section className="lg:col-span-8 surface-card overflow-hidden">
              <div className="px-5 py-3.5 border-b border-[#E6E2D8]">
                <h2 className="text-sm font-semibold text-[#142B4A]">Popular Research Topics</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#FAF8F2] text-[#697386] border-b border-[#E6E2D8]">
                    <tr>
                      <th className="px-5 py-3 font-medium">Research Topic</th>
                      <th className="px-4 py-3 font-medium">Recent Activity</th>
                      <th className="px-4 py-3 font-medium">Change</th>
                      {user && <th className="px-5 py-3 font-medium text-right">Follow</th>}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#F0ECE2]">
                    {(data?.trending_topics || []).slice(0, 14).map((t: any) => {
                      const isFol = followedTopics.includes(t.topic);
                      return (
                        <tr key={t.topic} className="hover:bg-[#FAF8F2]">
                          <td className="px-5 py-3">
                            <Link
                              to={`/search?q=${encodeURIComponent(t.topic.replace(/-/g, ' '))}`}
                              className="font-medium text-[#142B4A] hover:text-[#8E6914]"
                            >
                              {formatTopicLabel(t.topic)}
                            </Link>
                            {t.is_spike && <span className="ml-2 subtle-badge">Rising</span>}
                          </td>
                          <td className="px-4 py-3 text-[#3B485C]">{t.recent_count} interactions</td>
                          <td className={`px-4 py-3 font-medium ${t.growth_pct >= 0 ? 'text-[#8E6914]' : 'text-[#697386]'}`}>
                            {t.growth_pct >= 0 ? `+${t.growth_pct}%` : `${t.growth_pct}%`}
                          </td>
                          {user && (
                            <td className="px-5 py-3 text-right">
                              <button
                                onClick={() => toggleTopic(t.topic)}
                                className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium border ${
                                  isFol
                                    ? 'bg-[#E9EFE8] border-[#CFE0CC] text-[#2E5438]'
                                    : 'bg-white border-[#DCD7CA] text-[#263247] hover:bg-[#FAF8F2]'
                                }`}
                              >
                                {isFol ? <Check className="h-3 w-3" /> : <Plus className="h-3 w-3" />}
                                {isFol ? 'Following' : 'Follow'}
                              </button>
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="lg:col-span-4 surface-card p-5 space-y-3">
              <h2 className="text-sm font-semibold text-[#142B4A]">Popular Discussions</h2>
              <div className="space-y-2.5 divide-y divide-[#F0ECE2]">
                {popularPosts.map((po) => (
                  <Link key={po.id} to={`/discussions?post=${po.id}`} className="block pt-2.5 first:pt-0 group">
                    <div className="text-xs font-medium text-[#142B4A] group-hover:text-[#8E6914] line-clamp-2 leading-snug">
                      {po.title}
                    </div>
                    <div className="text-[11px] text-[#697386] mt-0.5">
                      {po.author?.full_name} · {po.upvote_count} upvotes · {po.comment_count} replies
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
