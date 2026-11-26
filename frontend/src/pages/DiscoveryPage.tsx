import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { BookOpen, ChevronLeft, ChevronRight, Filter, Search, TrendingUp } from 'lucide-react';
import { api } from '../services/api';
import PaperCard from '../components/PaperCard';
import { CardSkeleton, EmptyState, formatTopicLabel } from '../components/UIPrimitives';

const SUGGESTED_SEARCHES = [
  'Retrieval-augmented generation',
  'Graph neural networks',
  'Federated learning',
  'Solid-state batteries',
  'Bioinformatics genomics',
];

const PAGE_SIZE = 10;

export default function DiscoveryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [department, setDepartment] = useState(searchParams.get('department') || '');
  const [author, setAuthor] = useState('');
  const [source, setSource] = useState('');
  const [yearFrom, setYearFrom] = useState('');
  const [sort, setSort] = useState('saves');
  const [page, setPage] = useState(0);

  const [departments, setDepartments] = useState<any[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [papers, setPapers] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/api/departments').catch(() => []),
      api.get('/api/trends?window_days=14').catch(() => ({ trending_topics: [] })),
    ]).then(([d, t]) => {
      setDepartments(d || []);
      setTrends((t.trending_topics || []).slice(0, 8));
    });
  }, []);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams({
      sort,
      limit: String(PAGE_SIZE),
      offset: String(page * PAGE_SIZE),
    });
    if (query.trim()) params.set('q', query.trim());
    if (department) params.set('department', department);
    if (author.trim()) params.set('author', author.trim());
    if (source) params.set('source', source);
    if (yearFrom) params.set('year_from', yearFrom);

    api
      .get(`/api/papers?${params.toString()}`)
      .then((res) => {
        setPapers(res.items || []);
        setTotal(res.total || 0);
      })
      .finally(() => setLoading(false));
  }, [query, department, author, source, yearFrom, sort, page]);

  const handleFullSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  const resetFilters = () => {
    setQuery('');
    setDepartment('');
    setAuthor('');
    setSource('');
    setYearFrom('');
    setSort('saves');
    setPage(0);
    setSearchParams({});
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      {/* Image-Led Campus Explore Header */}
      <div className="grid md:grid-cols-3 gap-4">
        <button
          type="button"
          onClick={() => {
            setDepartment('CSAI');
            setPage(0);
          }}
          className="surface-card-interactive overflow-hidden text-left group"
        >
          <img
            src="/images/chanakya/Workshop5.jpg"
            alt="Chanakya University seminar workshop"
            className="h-32 w-full object-cover group-hover:scale-[1.02] transition-transform duration-200"
          />
          <div className="p-4 space-y-1">
            <div className="text-[11px] font-semibold text-[#8E6914]">Seminars & AI</div>
            <div className="text-sm font-semibold text-[#142B4A]">Faculty & Student Research</div>
            <p className="text-xs text-[#697386]">Explore AI, data science, and interdisciplinary studies.</p>
          </div>
        </button>

        <button
          type="button"
          onClick={() => {
            setDepartment('REM');
            setPage(0);
          }}
          className="surface-card-interactive overflow-hidden text-left group"
        >
          <img
            src="/images/chanakya/Sustainability-Web-Banner.jpg"
            alt="Chanakya Centre for Sustainability"
            className="h-32 w-full object-cover object-top group-hover:scale-[1.02] transition-transform duration-200"
          />
          <div className="p-4 space-y-1">
            <div className="text-[11px] font-semibold text-[#2E5438]">Sustainability & Energy</div>
            <div className="text-sm font-semibold text-[#142B4A]">Clean Energy & Materials</div>
            <p className="text-xs text-[#697386]">Discover papers in renewables, batteries, and climate.</p>
          </div>
        </button>

        <Link to="/researchers" className="surface-card-interactive overflow-hidden text-left group">
          <img
            src="/images/chanakya/CU-New-Campus-Infra_241.jpg"
            alt="Chanakya University learning hall"
            className="h-32 w-full object-cover group-hover:scale-[1.02] transition-transform duration-200"
          />
          <div className="p-4 space-y-1">
            <div className="text-[11px] font-semibold text-[#8E6914]">Campus People</div>
            <div className="text-sm font-semibold text-[#142B4A]">Meet Mentors & Peers</div>
            <p className="text-xs text-[#697386]">Find collaborators across Chanakya University schools.</p>
          </div>
        </Link>
      </div>

      {/* Approachable Discovery Search Bar */}
      <div className="surface-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Explore Research</h1>
            <p className="text-sm text-[#697386] mt-0.5">
              Browse interesting papers, shared campus readings, and active topics across departments.
            </p>
          </div>
          <span className="text-xs font-medium text-[#697386]">
            {total.toLocaleString()} publications
          </span>
        </div>

        <form onSubmit={handleFullSearch} className="flex flex-col sm:flex-row gap-2.5">
          <div className="relative flex-1">
            <Search className="h-4 w-4 text-[#8A92A0] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(0);
              }}
              placeholder="Filter publications by title, topic, or author..."
              className="input-field pl-10 py-2.5"
            />
          </div>
          <button type="submit" className="btn-primary px-5">
            Full Campus Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="text-[#8A92A0]">Popular topics:</span>
          {SUGGESTED_SEARCHES.map((sq) => (
            <button
              key={sq}
              type="button"
              onClick={() => navigate(`/search?q=${encodeURIComponent(sq)}`)}
              className="topic-pill"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Filter Sidebar + Results */}
      <div className="grid lg:grid-cols-12 gap-6 items-start">
        <aside className="lg:col-span-3 space-y-4">
          <div className="surface-card p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide flex items-center gap-1.5">
                <Filter className="h-3.5 w-3.5 text-[#8E6914]" /> Filter
              </h2>
              {(department || author || source || yearFrom || query) && (
                <button onClick={resetFilters} className="text-[11px] font-medium text-[#8E6914] hover:underline">
                  Reset
                </button>
              )}
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-[#3B485C] mb-1">Department</label>
                <select
                  value={department}
                  onChange={(e) => {
                    setDepartment(e.target.value);
                    setPage(0);
                  }}
                  className="input-field text-xs bg-white py-1.5"
                >
                  <option value="">All departments</option>
                  {departments.map((d) => (
                    <option key={d.code} value={d.code}>{d.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#3B485C] mb-1">Author</label>
                <input
                  value={author}
                  onChange={(e) => {
                    setAuthor(e.target.value);
                    setPage(0);
                  }}
                  placeholder="Author name..."
                  className="input-field text-xs py-1.5"
                />
              </div>

              <div>
                <label className="block font-medium text-[#3B485C] mb-1">Published since</label>
                <select
                  value={yearFrom}
                  onChange={(e) => {
                    setYearFrom(e.target.value);
                    setPage(0);
                  }}
                  className="input-field text-xs bg-white py-1.5"
                >
                  <option value="">Any year</option>
                  <option value="2025">2025 – Present</option>
                  <option value="2023">2023 – Present</option>
                  <option value="2021">2021 – Present</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-[#3B485C] mb-1">Sort order</label>
                <select
                  value={sort}
                  onChange={(e) => {
                    setSort(e.target.value);
                    setPage(0);
                  }}
                  className="input-field text-xs bg-white py-1.5"
                >
                  <option value="saves">Most Saved on Campus</option>
                  <option value="citations">Most Cited</option>
                  <option value="pagerank">Most Influential</option>
                  <option value="recent">Newest First</option>
                </select>
              </div>

              <div className="pt-2 border-t border-[#F0ECE2]">
                <label className="block font-medium text-[#697386] mb-1">Archive source (optional)</label>
                <select
                  value={source}
                  onChange={(e) => {
                    setSource(e.target.value);
                    setPage(0);
                  }}
                  className="input-field text-xs bg-white py-1.5"
                >
                  <option value="">All scholarly archives</option>
                  <option value="openalex">OpenAlex</option>
                  <option value="arxiv">arXiv</option>
                  <option value="rss">Research Feeds</option>
                </select>
              </div>
            </div>
          </div>

          {trends.length > 0 && (
            <div className="surface-card p-4 space-y-2.5">
              <h2 className="text-xs font-semibold text-[#142B4A] uppercase tracking-wide flex items-center gap-1.5">
                <TrendingUp className="h-3.5 w-3.5 text-[#8E6914]" /> Topics People Explore
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {trends.map((t) => (
                  <Link
                    key={t.topic}
                    to={`/search?q=${encodeURIComponent(t.topic.replace(/-/g, ' '))}`}
                    className="topic-pill"
                  >
                    {formatTopicLabel(t.topic)}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </aside>

        <div className="lg:col-span-9 space-y-4">
          {loading ? (
            <CardSkeleton rows={4} />
          ) : papers.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No publications matched"
              description="Try adjusting your department, year, or search keywords."
              action={<button onClick={resetFilters} className="btn-secondary text-xs">Clear Filters</button>}
            />
          ) : (
            <>
              <div className="space-y-3">
                {papers.map((p) => (
                  <PaperCard key={p.id} paper={p} />
                ))}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-between pt-2">
                  <span className="text-xs text-[#697386]">
                    Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, total)} of {total}
                  </span>
                  <div className="flex items-center gap-2">
                    <button
                      disabled={page === 0}
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      className="btn-secondary text-xs py-1.5 px-3"
                    >
                      <ChevronLeft className="h-3.5 w-3.5" /> Previous
                    </button>
                    <span className="text-xs font-medium text-[#142B4A] px-2">
                      Page {page + 1} of {totalPages}
                    </span>
                    <button
                      disabled={page + 1 >= totalPages}
                      onClick={() => setPage((p) => p + 1)}
                      className="btn-secondary text-xs py-1.5 px-3"
                    >
                      Next <ChevronRight className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
