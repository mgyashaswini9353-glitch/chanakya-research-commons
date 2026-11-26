import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  Database,
  RefreshCw,
  Shield,
  UserX,
} from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';
import { CardSkeleton, formatTopicLabel } from '../components/UIPrimitives';

export default function AdminPage() {
  const { showToast } = useToast();
  const [tab, setTab] = useState<'alerts' | 'accounts' | 'sources' | 'diagnostics'>('alerts');
  const [alerts, setAlerts] = useState<any[]>([]);
  const [spam, setSpam] = useState<any>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [evals, setEvals] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadAll = async () => {
    setError('');
    try {
      const [al, sp, jb, ev] = await Promise.all([
        api.get('/api/admin/alerts'),
        api.get('/api/admin/spam-report'),
        api.get('/api/admin/ingestion-jobs'),
        api.get('/api/admin/evaluations'),
      ]);
      setAlerts(al || []);
      setSpam(sp);
      setJobs(jb || []);
      setEvals(ev);
    } catch (err: any) {
      setError(err.message || 'Administrator access is required.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const updateAlert = async (id: number, status: string) => {
    await api.patch(`/api/admin/alerts/${id}`, { status });
    showToast('Alert status updated');
    loadAll();
  };

  const toggleUser = async (uid: number, currentlyActive: boolean) => {
    await api.post(`/api/admin/users/${uid}/toggle-active`);
    showToast(currentlyActive ? 'Account suspended' : 'Account reactivated', 'info');
    loadAll();
  };

  const syncLibrarySource = async (source: string) => {
    setBusy(true);
    try {
      await api.post('/api/admin/ingestion/run', { source, per_query: 8 });
      showToast('Research library updated successfully');
      await loadAll();
    } catch (err: any) {
      showToast(err.message || 'Could not update research sources', 'error');
    } finally {
      setBusy(false);
    }
  };

  if (error) {
    return (
      <div className="surface-card p-10 text-center text-sm text-[#142B4A] font-medium">
        {error}
      </div>
    );
  }

  if (loading) return <CardSkeleton rows={3} />;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Administration & Moderation</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Review flagged accounts, emerging topic notices, and external scholarly library updates.
          </p>
        </div>
        <Link to="/analytics" className="btn-secondary text-xs">
          Institutional Insights
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[#E6E2D8]">
        {[
          { id: 'alerts', label: `Moderation Alerts (${alerts.length})`, icon: Shield },
          { id: 'accounts', label: `Flagged Accounts (${spam?.flagged_count ?? 0})`, icon: UserX },
          { id: 'sources', label: `Library Updates (${jobs.length})`, icon: Database },
          { id: 'diagnostics', label: 'System Diagnostics', icon: Activity },
        ].map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id as any)}
              className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                tab === t.id
                  ? 'border-[#D6AA35] text-[#142B4A]'
                  : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              <Icon className="h-4 w-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {/* Alerts Tab */}
      {tab === 'alerts' && (
        <div className="space-y-3">
          {alerts.map((a) => {
            const isTopic = a.alert_type === 'topic_spike';
            const cleanTitle = isTopic
              ? `Growing interest in ${formatTopicLabel(a.entity_id)}`
              : a.title.replace('Suspicious / Spam Account Flagged:', 'Account flagged for review:');
            const cleanDesc = isTopic
              ? `Notable surge in university activity around ${formatTopicLabel(a.entity_id)}.`
              : 'This account has unusual activity patterns and has been flagged for review.';

            return (
              <div key={a.id} className="surface-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 text-[11px] font-medium">
                    <span
                      className={`rounded px-2 py-0.5 ${
                        isTopic ? 'bg-[#E9EFE8] text-[#2E5438]' : 'bg-amber-50 text-amber-800'
                      }`}
                    >
                      {isTopic ? 'Emerging Topic' : 'Account Review'}
                    </span>
                    <span className="text-[#8A92A0] capitalize">{a.status.replace('_', ' ')}</span>
                  </div>
                  <div className="text-sm font-semibold text-[#142B4A]">{cleanTitle}</div>
                  <p className="text-xs text-[#697386]">{cleanDesc}</p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => updateAlert(a.id, 'reviewed')} className="btn-secondary text-xs py-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-[#8E6914]" /> Mark Reviewed
                  </button>
                  {!isTopic && (
                    <button
                      onClick={() => updateAlert(a.id, 'action_taken')}
                      className="rounded-md bg-rose-600 text-white px-3 py-1.5 text-xs font-medium hover:bg-rose-700"
                    >
                      Suspend Account
                    </button>
                  )}
                  <button onClick={() => updateAlert(a.id, 'dismissed')} className="btn-ghost text-xs">
                    Dismiss
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Flagged Accounts Tab */}
      {tab === 'accounts' && spam && (
        <div className="surface-card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-[#E6E2D8] flex items-center justify-between">
            <div>
              <div className="text-sm font-semibold text-[#142B4A]">Accounts Flagged for Unusual Activity</div>
              <div className="text-xs text-[#697386]">
                {spam.flagged_count} of {spam.total_users_analyzed} accounts require moderator review.
              </div>
            </div>
            <button
              onClick={async () => {
                await api.get('/api/admin/spam-report?rescan=true');
                showToast('Account activity review refreshed');
                loadAll();
              }}
              className="btn-secondary text-xs py-1.5"
            >
              Run Activity Review
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF8F2] text-[#697386] border-b border-[#E6E2D8]">
                <tr>
                  <th className="px-5 py-3 font-medium">Member</th>
                  <th className="px-4 py-3 font-medium">Priority</th>
                  <th className="px-4 py-3 font-medium">Review Reasons</th>
                  <th className="px-5 py-3 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE2]">
                {spam.flagged_accounts.map((acc: any) => (
                  <tr key={acc.user_id} className="hover:bg-[#FAF8F2]">
                    <td className="px-5 py-3">
                      <div className="font-semibold text-[#142B4A]">{acc.full_name}</div>
                      <div className="text-[11px] text-[#697386]">@{acc.username} · {acc.department_code}</div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded px-2 py-0.5 text-[11px] font-medium capitalize ${
                          acc.risk_level === 'high' ? 'bg-rose-50 text-rose-800' : 'bg-amber-50 text-amber-800'
                        }`}
                      >
                        {acc.risk_level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#3B485C] max-w-md">
                      {(acc.reasons || []).slice(0, 2).join('; ')}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <button
                        onClick={() => toggleUser(acc.user_id, acc.is_active)}
                        className={
                          acc.is_active
                            ? 'rounded-md bg-rose-600 text-white px-3 py-1.5 text-xs font-medium hover:bg-rose-700'
                            : 'btn-accent text-xs py-1.5 px-3'
                        }
                      >
                        {acc.is_active ? 'Suspend' : 'Reactivate'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Scholarly Sources Sync Tab */}
      {tab === 'sources' && (
        <div className="space-y-4">
          <div className="surface-card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <div className="text-sm font-semibold text-[#142B4A]">Refresh External Scholarly Archives</div>
              <div className="text-xs text-[#697386]">
                Fetch new publications from open scholarly indexes and update the university catalog.
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              {[
                { id: 'openalex', label: 'Sync OpenAlex' },
                { id: 'arxiv', label: 'Sync arXiv' },
                { id: 'rss', label: 'Sync Research Feeds' },
              ].map((src) => (
                <button key={src.id} disabled={busy} onClick={() => syncLibrarySource(src.id)} className="btn-secondary text-xs">
                  <RefreshCw className={`h-3.5 w-3.5 ${busy ? 'animate-spin' : ''}`} /> {src.label}
                </button>
              ))}
            </div>
          </div>

          <div className="surface-card overflow-hidden">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#FAF8F2] text-[#697386] border-b border-[#E6E2D8]">
                <tr>
                  <th className="px-5 py-3 font-medium">Source</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Checked</th>
                  <th className="px-4 py-3 font-medium">New Papers Added</th>
                  <th className="px-5 py-3 font-medium">Duplicates Merged</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F0ECE2]">
                {jobs.map((j) => (
                  <tr key={j.id}>
                    <td className="px-5 py-3 font-medium text-[#142B4A] capitalize">{j.source}</td>
                    <td className="px-4 py-3">
                      <span className={j.status === 'completed' ? 'subtle-badge' : 'rounded px-2 py-0.5 bg-rose-50 text-rose-800 text-[11px]'}>
                        {j.status === 'completed' ? 'Updated' : j.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[#3B485C]">{j.records_fetched}</td>
                    <td className="px-4 py-3 text-[#2E5438] font-medium">{j.records_inserted}</td>
                    <td className="px-5 py-3 text-[#3B485C]">{j.records_merged}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Restricted Technical Monitoring & Quality Benchmarks Tab */}
      {tab === 'diagnostics' && (
        <div className="surface-card p-6 space-y-4">
          <div>
            <h2 className="text-sm font-semibold text-[#142B4A]">Platform Quality Benchmarks (Admin Only)</h2>
            <p className="text-xs text-[#697386]">
              Internal search, recommendation, deduplication, moderation, and assistant accuracy reports.
            </p>
          </div>
          {!evals?.available ? (
            <p className="text-xs text-[#697386]">{evals?.message}</p>
          ) : (
            <div className="grid md:grid-cols-2 gap-4 text-xs">
              <div className="rounded-md border border-[#E6E2D8] p-4 space-y-2">
                <div className="font-semibold text-[#142B4A]">Search Relevance</div>
                {['keyword', 'semantic', 'hybrid'].map((m) => (
                  <div key={m} className="flex justify-between py-1 border-b border-[#F0ECE2] last:border-0">
                    <span className="capitalize text-[#3B485C]">{m}</span>
                    <span className="font-medium text-[#142B4A]">
                      P@5 {evals.results.search[m].precision_at_5} · NDCG@10 {evals.results.search[m].ndcg_at_10}
                    </span>
                  </div>
                ))}
              </div>
              <div className="rounded-md border border-[#E6E2D8] p-4 space-y-2">
                <div className="font-semibold text-[#142B4A]">Recommendation Quality</div>
                <div className="flex justify-between py-1 border-b border-[#F0ECE2]">
                  <span className="text-[#3B485C]">Popularity Baseline</span>
                  <span>P@5 {evals.results.recommendations.popularity_baseline.precision_at_5} · R@10 {evals.results.recommendations.popularity_baseline.recall_at_10}</span>
                </div>
                <div className="flex justify-between py-1 text-[#2E5438] font-semibold">
                  <span>Personalized Engine</span>
                  <span>P@5 {evals.results.recommendations.hybrid_content_cf.precision_at_5} · R@10 {evals.results.recommendations.hybrid_content_cf.recall_at_10}</span>
                </div>
              </div>
              <div className="rounded-md border border-[#E6E2D8] p-4 space-y-2">
                <div className="font-semibold text-[#142B4A]">Record Deduplication</div>
                <div className="flex justify-between py-1 border-b border-[#F0ECE2]">
                  <span className="text-[#3B485C]">Exact Match Baseline</span>
                  <span>F1 {evals.results.duplicate_detection.exact_match_baseline.f1_score}</span>
                </div>
                <div className="flex justify-between py-1 text-[#2E5438] font-semibold">
                  <span>Entity Resolution Pipeline</span>
                  <span>F1 {evals.results.duplicate_detection.minhash_lsh_entity_resolution.f1_score}</span>
                </div>
              </div>
              <div className="rounded-md border border-[#E6E2D8] p-4 space-y-2">
                <div className="font-semibold text-[#142B4A]">Moderation, Trends & Assistant</div>
                <div className="flex justify-between py-1 border-b border-[#F0ECE2]">
                  <span className="text-[#3B485C]">Spam Detection F1</span>
                  <span className="font-semibold text-[#2E5438]">{evals.results.spam_detection.isolation_forest_behavioral.f1_score}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-[#F0ECE2]">
                  <span className="text-[#3B485C]">Trend Detection Rate</span>
                  <span className="font-semibold text-[#2E5438]">{evals.results.trend_detection.detection_rate} (0 false alarms)</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-[#3B485C]">Assistant Citation Accuracy</span>
                  <span className="font-semibold text-[#2E5438]">{evals.results.rag_assistant.citation_correctness}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
