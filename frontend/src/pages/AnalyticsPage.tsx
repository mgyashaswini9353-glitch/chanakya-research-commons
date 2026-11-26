import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { ChevronRight, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';
import { CardSkeleton, formatTopicLabel } from '../components/UIPrimitives';

export default function AnalyticsPage() {
  const { showToast } = useToast();
  const [overview, setOverview] = useState<any>(null);
  const [drill, setDrill] = useState<any>(null);
  const [selDept, setSelDept] = useState<string | null>(null);
  const [selTopic, setSelTopic] = useState<string | null>(null);
  const [selMember, setSelMember] = useState<number | null>(null);
  const [rebuilding, setRebuilding] = useState(false);
  const [error, setError] = useState('');

  const loadOverview = async () => {
    setError('');
    try {
      const ov = await api.get('/api/analytics/overview');
      setOverview(ov);
    } catch (err: any) {
      setError(err.message || 'Administrator access is required to view Institutional Insights.');
    }
  };

  const loadDrill = async (dept: string | null, topic: string | null, member: number | null) => {
    const params = new URLSearchParams();
    if (dept) params.set('department_code', dept);
    if (topic) params.set('topic_name', topic);
    if (member) params.set('member_id', String(member));
    const d = await api.get(`/api/analytics/drilldown?${params.toString()}`);
    setDrill(d);
  };

  useEffect(() => {
    loadOverview();
    loadDrill(null, null, null).catch(() => {});
  }, []);

  const handleRefresh = async () => {
    setRebuilding(true);
    try {
      await api.post('/api/analytics/rebuild-warehouse');
      await loadOverview();
      await loadDrill(selDept, selTopic, selMember);
      showToast('Institutional insights refreshed');
    } catch (err: any) {
      showToast(err.message || 'Unable to refresh insights', 'error');
    } finally {
      setRebuilding(false);
    }
  };

  if (error) {
    return (
      <div className="surface-card p-10 text-center space-y-2">
        <div className="text-base font-semibold text-[#142B4A]">{error}</div>
        <p className="text-xs text-[#697386]">
          Please sign in with an authorized administrator account to access university-wide insights.
        </p>
      </div>
    );
  }

  if (!overview) return <CardSkeleton rows={4} />;

  const k = overview.kpis;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Institutional Insights</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            University-wide research participation, cross-departmental collaboration, and reading engagement.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/admin" className="btn-secondary text-xs">
            Administration
          </Link>
          <button onClick={handleRefresh} disabled={rebuilding} className="btn-primary text-xs">
            <RefreshCw className={`h-3.5 w-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
            {rebuilding ? 'Updating...' : 'Refresh Insights'}
          </button>
        </div>
      </div>

      {/* Executive Summary Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: 'Indexed Publications', value: k.total_papers?.toLocaleString(), note: `${k.university_library_papers} saved on campus` },
          { label: 'University Members', value: k.total_members?.toLocaleString(), note: `${k.total_departments} active departments` },
          { label: 'Library Saves', value: k.total_saves?.toLocaleString(), note: 'Shared campus holdings' },
          { label: 'Community Discussions', value: (k.total_posts + k.total_comments)?.toLocaleString(), note: `${k.total_posts} posts · ${k.total_comments} replies` },
          { label: 'Research Activity', value: k.total_activity_events?.toLocaleString(), note: 'Past 6 months' },
        ].map((item) => (
          <div key={item.label} className="surface-card p-4">
            <div className="text-xs font-medium text-[#697386]">{item.label}</div>
            <div className="text-2xl font-semibold text-[#142B4A] mt-1">{item.value}</div>
            <div className="text-[11px] text-[#8A92A0] mt-0.5">{item.note}</div>
          </div>
        ))}
      </div>

      {/* Activity Over Time & Department Comparison Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        <section className="surface-card p-5 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[#142B4A]">Research Activity Over Time</h2>
            <p className="text-xs text-[#697386]">Monthly reads, searches, saves, and discussions across campus.</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={overview.monthly_trends}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E2D8" />
                <XAxis dataKey="month_name" tick={{ fontSize: 11, fill: '#697386' }} />
                <YAxis tick={{ fontSize: 11, fill: '#697386' }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #E6E2D8', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="views" stackId="1" stroke="#142B4A" fill="#142B4A" fillOpacity={0.75} name="Reads" />
                <Area type="monotone" dataKey="searches" stackId="1" stroke="#8E6914" fill="#8E6914" fillOpacity={0.7} name="Searches" />
                <Area type="monotone" dataKey="discussions" stackId="1" stroke="#64748B" fill="#64748B" fillOpacity={0.65} name="Discussions" />
                <Area type="monotone" dataKey="saves" stackId="1" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.75} name="Library Saves" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="surface-card p-5 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[#142B4A]">Participation by Department</h2>
            <p className="text-xs text-[#697386]">Comparison of reading, search, discussion, and library activity.</p>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={overview.department_comparison}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E6E2D8" />
                <XAxis dataKey="department_code" tick={{ fontSize: 11, fill: '#697386' }} />
                <YAxis tick={{ fontSize: 11, fill: '#697386' }} />
                <Tooltip contentStyle={{ borderRadius: 8, border: '1px solid #E6E2D8', fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="views" fill="#142B4A" name="Reads" />
                <Bar dataKey="searches" fill="#8E6914" name="Searches" />
                <Bar dataKey="discussions" fill="#64748B" name="Discussions" />
                <Bar dataKey="saves" fill="#3B82F6" name="Saves" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>

      {/* Interactive 4-Level Department -> Topic -> Member Explorer */}
      <section className="surface-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-semibold text-[#142B4A]">
              Explore Research Activity by Department, Topic & Member
            </h2>
            <p className="text-xs text-[#697386]">
              Select a department below to inspect its leading research topics and contributing members.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs font-medium">
            <button
              onClick={() => {
                setSelDept(null);
                setSelTopic(null);
                setSelMember(null);
                loadDrill(null, null, null);
              }}
              className="text-[#8E6914] hover:underline"
            >
              University
            </button>
            {selDept && (
              <>
                <ChevronRight className="h-3.5 w-3.5 text-[#8A92A0]" />
                <button
                  onClick={() => {
                    setSelTopic(null);
                    setSelMember(null);
                    loadDrill(selDept, null, null);
                  }}
                  className="text-[#8E6914] hover:underline"
                >
                  {selDept}
                </button>
              </>
            )}
            {selTopic && (
              <>
                <ChevronRight className="h-3.5 w-3.5 text-[#8A92A0]" />
                <button
                  onClick={() => {
                    setSelMember(null);
                    loadDrill(selDept, selTopic, null);
                  }}
                  className="text-[#8E6914] hover:underline"
                >
                  {formatTopicLabel(selTopic)}
                </button>
              </>
            )}
            {selMember && (
              <>
                <ChevronRight className="h-3.5 w-3.5 text-[#8A92A0]" />
                <span className="text-[#142B4A]">Member Details</span>
              </>
            )}
          </div>
        </div>

        {drill?.level === 'university' && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {drill.departments.map((d: any) => (
              <button
                key={d.department_code}
                onClick={() => {
                  setSelDept(d.department_code);
                  loadDrill(d.department_code, null, null);
                }}
                className="text-left rounded-md border border-[#E6E2D8] p-4 hover:border-[#8E6914] hover:bg-[#FAF8F2] transition-colors"
              >
                <div className="text-xs font-semibold text-[#8E6914]">{d.department_code}</div>
                <div className="text-sm font-semibold text-[#142B4A] mt-0.5">{d.department_name}</div>
                <div className="text-xs text-[#697386] mt-1">
                  {d.events.toLocaleString()} activities · {d.active_members} active members
                </div>
              </button>
            ))}
          </div>
        )}

        {drill?.level === 'department' && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {drill.topics.map((t: any) => (
              <button
                key={t.topic_name}
                onClick={() => {
                  setSelTopic(t.topic_name);
                  loadDrill(selDept, t.topic_name, null);
                }}
                className="text-left rounded-md border border-[#E6E2D8] p-3.5 hover:border-[#8E6914] hover:bg-[#FAF8F2]"
              >
                <div className="text-xs font-semibold text-[#142B4A]">{formatTopicLabel(t.topic_name)}</div>
                <div className="text-[11px] text-[#697386] mt-1">
                  {t.events} activities · {t.active_members} members
                </div>
              </button>
            ))}
          </div>
        )}

        {drill?.level === 'topic' && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {drill.members.map((m: any) => (
              <button
                key={m.id}
                onClick={() => {
                  setSelMember(m.id);
                  loadDrill(selDept, selTopic, m.id);
                }}
                className="text-left rounded-md border border-[#E6E2D8] p-3.5 hover:border-[#8E6914] hover:bg-[#FAF8F2]"
              >
                <div className="text-xs font-semibold text-[#142B4A]">{m.full_name}</div>
                <div className="text-[11px] text-[#697386] capitalize mt-0.5">
                  {m.role} · {m.events} activities · {m.saves} saves
                </div>
              </button>
            ))}
          </div>
        )}

        {drill?.level === 'member' && drill.member && (
          <div className="grid md:grid-cols-2 gap-5 rounded-md border border-[#E6E2D8] bg-[#FAF8F2] p-4">
            <div className="space-y-2.5">
              <div className="text-sm font-semibold text-[#142B4A]">
                {drill.member.full_name} · <span className="capitalize font-normal text-[#697386]">{drill.member.role} ({drill.member.department_code})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {drill.top_topics.map((t: any) => (
                  <span key={t.topic_name} className="topic-pill">
                    {formatTopicLabel(t.topic_name)} ({t.events})
                  </span>
                ))}
              </div>
              <Link to={`/researchers/${drill.member.id}`} className="inline-block text-xs font-medium text-[#8E6914] hover:underline">
                Open Member Profile →
              </Link>
            </div>
            <div className="space-y-1.5">
              <div className="text-xs font-semibold text-[#142B4A]">Saved Publications ({drill.saved_papers.length})</div>
              {drill.saved_papers.slice(0, 5).map((p: any) => (
                <Link key={p.id} to={`/papers/${p.id}`} className="block text-xs text-[#3B485C] hover:text-[#8E6914] truncate">
                  • {p.title}
                </Link>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* Cross-Department Collaboration + Research Theme Groups */}
      <div className="grid lg:grid-cols-2 gap-6">
        <section className="surface-card p-5 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[#142B4A]">Cross-Department Research Overlap</h2>
            <p className="text-xs text-[#697386]">Shared literature read and saved jointly across pairs of departments.</p>
          </div>
          <div className="space-y-2">
            {(overview.cross_department_collaboration || []).slice(0, 8).map((c: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between text-xs px-3.5 py-2.5 rounded-md bg-[#FAF8F2] border border-[#F0ECE2]">
                <span className="font-semibold text-[#142B4A]">{c.dept_a} & {c.dept_b}</span>
                <span className="subtle-badge">{c.shared_papers} shared publications</span>
              </div>
            ))}
          </div>
        </section>

        <section className="surface-card p-5 space-y-3">
          <div>
            <h2 className="text-sm font-semibold text-[#142B4A]">University Research Theme Groups</h2>
            <p className="text-xs text-[#697386]">Related topics frequently explored together across departments.</p>
          </div>
          <div className="space-y-2.5">
            {(overview.topic_clusters || []).map((cl: any) => (
              <div key={cl.cluster_id} className="rounded-md border border-[#E6E2D8] p-3 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-[#142B4A]">
                    {formatTopicLabel(cl.topics?.[0]?.topic || cl.label)} & Related Areas
                  </span>
                  <span className="text-[#697386]">{cl.total_activity} interactions</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {cl.topics.map((t: any) => (
                    <span key={t.topic} className="topic-pill">{formatTopicLabel(t.topic)}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Most Saved & Most Discussed */}
      <div className="grid lg:grid-cols-2 gap-6">
        <section className="surface-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#142B4A]">Most Saved Publications</h2>
          <div className="divide-y divide-[#F0ECE2]">
            {overview.most_saved_papers.slice(0, 7).map((p: any) => (
              <Link key={p.id} to={`/papers/${p.id}`} className="flex items-center justify-between gap-3 py-2.5 text-xs hover:text-[#8E6914]">
                <span className="font-medium text-[#263247] truncate">{p.title}</span>
                <span className="shrink-0 text-[#697386]">{p.save_count} saves · {p.dept_reach} depts</span>
              </Link>
            ))}
          </div>
        </section>

        <section className="surface-card p-5 space-y-3">
          <h2 className="text-sm font-semibold text-[#142B4A]">Most Discussed Research Threads</h2>
          <div className="divide-y divide-[#F0ECE2]">
            {overview.most_discussed_papers.slice(0, 7).map((p: any) => (
              <Link key={p.post_id} to={`/discussions?post=${p.post_id}`} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                <div className="min-w-0">
                  <div className="font-medium text-[#263247] truncate hover:text-[#8E6914]">{p.post_title}</div>
                  <div className="text-[11px] text-[#697386]">{p.author_name} · {p.department_code}</div>
                </div>
                <span className="shrink-0 text-[#697386]">{p.upvote_count} upvotes · {p.comment_count} replies</span>
              </Link>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
