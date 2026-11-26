import React, { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  BookMarked,
  BookOpen,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Search,
  SlidersHorizontal,
  Users,
} from 'lucide-react';
import { api } from '../services/api';
import PaperCard from '../components/PaperCard';
import {
  CardSkeleton,
  EmptyState,
  formatRelativeDate,
  formatTopicLabel,
  getInitials,
} from '../components/UIPrimitives';

type SearchTab = 'all' | 'papers' | 'library' | 'researchers' | 'discussions';
type SearchMode = 'hybrid' | 'semantic' | 'keyword';

const SUGGESTIONS = [
  'Retrieval augmented generation',
  'Federated learning',
  'Solid state batteries',
  'Protein folding',
  'Autonomous robotics',
];

export default function UnifiedSearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [mode, setMode] = useState<SearchMode>((searchParams.get('mode') as SearchMode) || 'hybrid');
  const [activeTab, setActiveTab] = useState<SearchTab>('all');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [department, setDepartment] = useState('');
  const [source, setSource] = useState('');
  const [yearFrom, setYearFrom] = useState('');
  const [departments, setDepartments] = useState<any[]>([]);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/api/departments').then(setDepartments).catch(() => {});
  }, []);

  const runSearch = async (qVal = query, mVal = mode) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('q', qVal);
      params.set('mode', mVal);
      if (department) params.set('department', department);
      if (source) params.set('source', source);
      if (yearFrom) params.set('year_from', yearFrom);
      params.set('limit', '15');
      const res = await api.get(`/api/search/unified?${params.toString()}`);
      setData(res);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const qParam = searchParams.get('q') || '';
    const mParam = (searchParams.get('mode') as SearchMode) || mode;
    setQuery(qParam);
    setMode(mParam);
    runSearch(qParam, mParam);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ q: query.trim(), mode });
    runSearch(query.trim(), mode);
  };

  const handleModeChange = (nextMode: SearchMode) => {
    setMode(nextMode);
    setSearchParams({ q: query.trim(), mode: nextMode });
    runSearch(query.trim(), nextMode);
  };

  const externalPapers = data?.panels?.external_papers || [];
  const libraryPapers = data?.panels?.university_library || [];
  const researchers = data?.panels?.researchers || [];
  const posts = data?.panels?.posts || [];
  const totalFound = externalPapers.length + libraryPapers.length + researchers.length + posts.length;

  const tabs: { id: SearchTab; label: string; count: number; icon: any }[] = [
    { id: 'all', label: 'All Results', count: totalFound, icon: Search },
    { id: 'papers', label: 'Papers', count: externalPapers.length, icon: BookOpen },
    { id: 'library', label: 'Library', count: libraryPapers.length, icon: BookMarked },
    { id: 'researchers', label: 'People', count: researchers.length, icon: Users },
    { id: 'discussions', label: 'Discussions', count: posts.length, icon: MessageSquare },
  ];

  const relevanceNote = (p: any, isLib = false) => {
    if (isLib && p.save_count > 0) {
      return `Saved by ${p.save_count} Chanakya ${p.save_count === 1 ? 'member' : 'members'}`;
    }
    if (mode === 'semantic') return 'Related by research concept';
    if (p.relevance_score && p.relevance_score > 0.7) return 'Highly relevant to your search';
    return undefined;
  };

  return (
    <div className="space-y-6">
      {/* Simple, Approachable Search Card */}
      <div className="surface-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Research Search</h1>
            <p className="text-sm text-[#697386] mt-0.5">
              Search papers, saved campus readings, faculty and students, and community discussions together.
            </p>
          </div>
          <Link to="/assistant" className="text-xs font-medium text-[#8E6914] hover:underline">
            Prefer asking a question? Try Research Assistant →
          </Link>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex flex-col sm:flex-row gap-2.5">
            <div className="relative flex-1">
              <Search className="h-4 w-4 text-[#8A92A0] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search any topic, author, paper, or question..."
                className="input-field pl-10 py-2.5"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary px-6">
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[#8A92A0]">Try:</span>
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => {
                    setQuery(s);
                    setSearchParams({ q: s, mode });
                    runSearch(s, mode);
                  }}
                  className="topic-pill"
                >
                  {s}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowAdvanced((v) => !v)}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-[#697386] hover:text-[#142B4A]"
            >
              <SlidersHorizontal className="h-3.5 w-3.5" />
              More search options
              {showAdvanced ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </button>
          </div>

          {/* Secondary Advanced Options (Tucked Away Cleanly) */}
          {showAdvanced && (
            <div className="pt-3 border-t border-[#F0ECE2] flex flex-wrap items-center gap-3 text-xs">
              <div className="inline-flex rounded-lg border border-[#DCD7CA] bg-[#FAF8F2] p-0.5">
                {[
                  { id: 'hybrid', label: 'Smart Search' },
                  { id: 'semantic', label: 'Concept Match' },
                  { id: 'keyword', label: 'Exact Terms' },
                ].map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    onClick={() => handleModeChange(m.id as SearchMode)}
                    className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                      mode === m.id ? 'bg-[#142B4A] text-white' : 'text-[#697386] hover:text-[#142B4A]'
                    }`}
                  >
                    {m.label}
                  </button>
                ))}
              </div>

              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="input-field w-auto text-xs bg-white py-1.5"
              >
                <option value="">All Departments</option>
                {departments.map((d) => (
                  <option key={d.code} value={d.code}>{d.name}</option>
                ))}
              </select>
              <select
                value={source}
                onChange={(e) => setSource(e.target.value)}
                className="input-field w-auto text-xs bg-white py-1.5"
              >
                <option value="">All Sources</option>
                <option value="openalex">OpenAlex</option>
                <option value="arxiv">arXiv</option>
                <option value="rss">Research Feeds</option>
              </select>
              <select
                value={yearFrom}
                onChange={(e) => setYearFrom(e.target.value)}
                className="input-field w-auto text-xs bg-white py-1.5"
              >
                <option value="">Any Year</option>
                <option value="2025">2025+</option>
                <option value="2023">2023+</option>
                <option value="2021">2021+</option>
              </select>
            </div>
          )}
        </form>
      </div>

      {/* Category Tabs */}
      <div className="flex items-center gap-1 overflow-x-auto border-b border-[#E6E2D8]">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                activeTab === t.id
                  ? 'border-[#D6AA35] text-[#142B4A]'
                  : 'border-transparent text-[#697386] hover:text-[#142B4A]'
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{t.label}</span>
              <span className="rounded-full bg-[#F3F4F2] px-2 py-0.5 text-[11px] font-semibold text-[#3B485C]">
                {t.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Results */}
      {loading && !data ? (
        <CardSkeleton rows={4} />
      ) : (
        <div className="space-y-8">
          {activeTab === 'all' && (
            <div className="grid lg:grid-cols-2 gap-6">
              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-[#8E6914]" /> Research Papers
                  </h2>
                  {externalPapers.length > 4 && (
                    <button onClick={() => setActiveTab('papers')} className="text-xs font-medium text-[#8E6914] hover:underline">
                      View all ({externalPapers.length})
                    </button>
                  )}
                </div>
                {externalPapers.length === 0 ? (
                  <EmptyState icon={BookOpen} title="No papers matched" description="Try broader keywords or open More search options." />
                ) : (
                  <div className="space-y-3">
                    {externalPapers.slice(0, 5).map((p: any) => (
                      <PaperCard key={`ext-${p.id}`} paper={p} highlightNote={relevanceNote(p)} />
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-2">
                    <BookMarked className="h-4 w-4 text-[#2E5438]" /> Chanakya University Library
                  </h2>
                  {libraryPapers.length > 4 && (
                    <button onClick={() => setActiveTab('library')} className="text-xs font-medium text-[#8E6914] hover:underline">
                      View all ({libraryPapers.length})
                    </button>
                  )}
                </div>
                {libraryPapers.length === 0 ? (
                  <EmptyState icon={BookMarked} title="No campus library items matched" description="Save papers from the left to share them with the university library." />
                ) : (
                  <div className="space-y-3">
                    {libraryPapers.slice(0, 5).map((p: any) => (
                      <PaperCard key={`lib-${p.id}`} paper={p} highlightNote={relevanceNote(p, true)} />
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-2">
                    <Users className="h-4 w-4 text-[#142B4A]" /> People on Campus
                  </h2>
                  {researchers.length > 4 && (
                    <button onClick={() => setActiveTab('researchers')} className="text-xs font-medium text-[#8E6914] hover:underline">
                      View all ({researchers.length})
                    </button>
                  )}
                </div>
                {researchers.length === 0 ? (
                  <EmptyState icon={Users} title="No members matched" description="Try searching by department or broader interest area." />
                ) : (
                  <div className="space-y-3">
                    {researchers.slice(0, 5).map((r: any) => (
                      <div key={r.id} className="surface-card-interactive p-4 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3 min-w-0">
                          <div className="h-10 w-10 rounded-full bg-[#142B4A] text-[#FBF5E4] flex items-center justify-center text-xs font-semibold shrink-0">
                            {getInitials(r.full_name)}
                          </div>
                          <div className="min-w-0">
                            <Link to={`/researchers/${r.id}`} className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] block">
                              {r.full_name}
                            </Link>
                            <div className="text-xs text-[#697386] capitalize">
                              {r.role} · {r.department_name || r.department_code}
                            </div>
                            <p className="text-xs text-[#3B485C] mt-1 line-clamp-2">{r.research_interests_text || r.bio}</p>
                            <div className="flex flex-wrap gap-1 mt-2">
                              {(r.research_tags || []).slice(0, 3).map((t: string) => (
                                <span key={t} className="topic-pill">{formatTopicLabel(t)}</span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <Link to={`/researchers/${r.id}`} className="btn-secondary text-xs py-1.5 px-3 shrink-0">
                          Profile
                        </Link>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="space-y-3">
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-2">
                    <MessageSquare className="h-4 w-4 text-[#142B4A]" /> Community Discussions
                  </h2>
                  {posts.length > 4 && (
                    <button onClick={() => setActiveTab('discussions')} className="text-xs font-medium text-[#8E6914] hover:underline">
                      View all ({posts.length})
                    </button>
                  )}
                </div>
                {posts.length === 0 ? (
                  <EmptyState icon={MessageSquare} title="No discussions matched" description="Start a new community post on this topic." />
                ) : (
                  <div className="space-y-3">
                    {posts.slice(0, 5).map((po: any) => (
                      <Link key={po.id} to={`/discussions?post=${po.id}`} className="surface-card-interactive p-4 block space-y-1.5">
                        <div className="text-sm font-semibold text-[#142B4A]">{po.title}</div>
                        <p className="text-xs text-[#3B485C] line-clamp-2">{po.content}</p>
                        <div className="flex items-center justify-between text-[11px] text-[#697386] pt-1">
                          <span>{po.author_name} · {po.department_code}</span>
                          <span>{po.upvote_count} likes · {po.comment_count} replies</span>
                        </div>
                      </Link>
                    ))}
                  </div>
                )}
              </section>
            </div>
          )}

          {activeTab === 'papers' && (
            <div className="space-y-3 max-w-4xl">
              {externalPapers.map((p: any) => <PaperCard key={p.id} paper={p} highlightNote={relevanceNote(p)} />)}
            </div>
          )}

          {activeTab === 'library' && (
            <div className="space-y-3 max-w-4xl">
              {libraryPapers.map((p: any) => <PaperCard key={p.id} paper={p} highlightNote={relevanceNote(p, true)} />)}
            </div>
          )}

          {activeTab === 'researchers' && (
            <div className="grid md:grid-cols-2 gap-4">
              {researchers.map((r: any) => (
                <div key={r.id} className="surface-card-interactive p-5 flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="h-10 w-10 rounded-full bg-[#142B4A] text-[#FBF5E4] flex items-center justify-center text-xs font-semibold shrink-0">
                      {getInitials(r.full_name)}
                    </div>
                    <div className="min-w-0">
                      <Link to={`/researchers/${r.id}`} className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] block">
                        {r.full_name}
                      </Link>
                      <div className="text-xs text-[#697386] capitalize">{r.role} · {r.department_name}</div>
                      <p className="text-xs text-[#3B485C] mt-1 line-clamp-2">{r.research_interests_text || r.bio}</p>
                    </div>
                  </div>
                  <Link to={`/researchers/${r.id}`} className="btn-secondary text-xs py-1.5 px-3 shrink-0">Profile</Link>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'discussions' && (
            <div className="space-y-3 max-w-4xl">
              {posts.map((po: any) => (
                <Link key={po.id} to={`/discussions?post=${po.id}`} className="surface-card-interactive p-5 block space-y-2">
                  <div className="text-base font-semibold text-[#142B4A]">{po.title}</div>
                  <p className="text-sm text-[#3B485C] line-clamp-2">{po.content}</p>
                  <div className="text-xs text-[#697386] pt-1">
                    {po.author_name} · {po.department_code} · {formatRelativeDate(po.created_at)} · {po.upvote_count} likes · {po.comment_count} replies
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
