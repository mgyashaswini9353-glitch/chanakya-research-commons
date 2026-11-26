import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  BookOpen,
  Compass,
  MessageSquare,
  Search,
  Sparkles,
  Users,
} from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { BrandLogo } from '../components/BrandLogo';
import PaperCard from '../components/PaperCard';
import { getInitials } from '../components/UIPrimitives';

const SUGGESTED_TOPICS = [
  'Retrieval-augmented generation',
  'Solid-state batteries',
  'Bioinformatics & genomics',
  'Federated learning',
];

export default function LandingPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [departments, setDepartments] = useState<any[]>([]);
  const [featuredPapers, setFeaturedPapers] = useState<any[]>([]);
  const [researchers, setResearchers] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([
      api.get('/api/departments').catch(() => []),
      api.get('/api/papers?only_library=true&sort=saves&limit=4').catch(() => ({ items: [] })),
      api.get('/api/users?limit=4').catch(() => []),
    ]).then(([depts, papersRes, usersRes]) => {
      setDepartments(depts || []);
      setFeaturedPapers(papersRes.items || []);
      setResearchers(usersRes || []);
    });
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/discover');
  };

  return (
    <div className="min-h-screen bg-[#FAF8F2] text-[#263247] flex flex-col">
      {/* Subtle Chanakya Gold top line */}
      <div className="h-[3px] bg-[#D6AA35] w-full" />

      {/* Clean White Header */}
      <header className="bg-white border-b border-[#E6E2D8] sticky top-0 z-30">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link to="/">
            <BrandLogo />
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-[#697386]">
            <Link to="/discussions" className="hover:text-[#142B4A] transition-colors">Community</Link>
            <Link to="/discover" className="hover:text-[#142B4A] transition-colors">Explore</Link>
            <Link to="/search" className="hover:text-[#142B4A] transition-colors">Research</Link>
            <Link to="/researchers" className="hover:text-[#142B4A] transition-colors">People</Link>
          </nav>

          <div className="flex items-center gap-2.5">
            {user ? (
              <Link to="/dashboard" className="btn-primary text-sm">
                Open Home <ArrowRight className="h-4 w-4" />
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost text-sm">
                  Sign in
                </Link>
                <Link to="/register" className="btn-primary text-sm">
                  Join Community
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Welcome Hero with Real Chanakya University Campus Photograph */}
      <section className="bg-white border-b border-[#E6E2D8]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 lg:py-16 grid lg:grid-cols-12 gap-10 items-center">
          <div className="lg:col-span-6 space-y-5">
            <div className="gold-badge">
              Chanakya University · Campus Research Community
            </div>

            <h1 className="text-3xl sm:text-[42px] font-semibold text-[#142B4A] tracking-tight leading-[1.15]">
              Ideas grow when we share them.
            </h1>

            <p className="text-base text-[#697386] leading-relaxed">
              Connect with curious minds, discover research across schools, share what you are building, and be part of the conversations shaping tomorrow.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <Link to={user ? '/dashboard' : '/discussions'} className="btn-primary py-2.5 px-5">
                Explore Community <ArrowRight className="h-4 w-4" />
              </Link>
              <Link to="/discover" className="btn-secondary py-2.5 px-5">
                Discover Research
              </Link>
            </div>

            {/* Clean Research Search */}
            <form onSubmit={handleSearch} className="pt-3 space-y-2.5">
              <div className="relative">
                <Search className="h-4 w-4 text-[#8A92A0] absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search papers, topics, faculty, or student projects..."
                  className="input-field pl-10 pr-24 py-2.5 bg-[#FAF8F2] focus:bg-white"
                />
                <button
                  type="submit"
                  className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md bg-[#142B4A] px-3.5 py-1.5 text-xs font-medium text-white hover:bg-[#0E2038]"
                >
                  Search
                </button>
              </div>
              <div className="flex flex-wrap items-center gap-1.5 text-xs">
                <span className="text-[#8A92A0]">Exploring now:</span>
                {SUGGESTED_TOPICS.map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => navigate(`/search?q=${encodeURIComponent(t)}`)}
                    className="topic-pill"
                  >
                    {t}
                  </button>
                ))}
              </div>
            </form>
          </div>

          <div className="lg:col-span-6">
            <div className="rounded-2xl overflow-hidden border border-[#E6E2D8] shadow-cardHover bg-[#FAF8F2]">
              <img
                src="/images/chanakya/campus.jpg"
                alt="Chanakya University Campus"
                className="w-full h-[300px] sm:h-[360px] object-cover"
              />
              <div className="px-5 py-3 bg-white border-t border-[#F0ECE2] flex items-center justify-between text-xs text-[#697386]">
                <span>Chanakya University Global Campus, Bengaluru</span>
                <span className="text-[#8E6914] font-medium">Open to all students & faculty</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Life & Learning on Campus — Thoughtful Selective Photo Cards */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 space-y-8">
        <div className="max-w-2xl">
          <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">
            A digital home for curiosity and collaboration
          </h2>
          <p className="text-sm text-[#697386] mt-1.5 leading-relaxed">
            Whether you are starting a literature review, sharing notes from a seminar, or looking for teammates on a project, everything starts here.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          <Link to="/discussions" className="surface-card-interactive overflow-hidden flex flex-col">
            <img
              src="/images/chanakya/Workshop5.jpg"
              alt="Chanakya University seminar and workshop"
              className="h-44 w-full object-cover"
            />
            <div className="p-5 space-y-2 flex-1">
              <div className="sage-badge">Community & Seminars</div>
              <h3 className="text-base font-semibold text-[#142B4A]">Share ideas & ask questions</h3>
              <p className="text-xs text-[#697386] leading-relaxed">
                Continue classroom conversations online, share reading notes, and collaborate with peers and faculty across schools.
              </p>
            </div>
          </Link>

          <Link to="/discover" className="surface-card-interactive overflow-hidden flex flex-col">
            <img
              src="/images/chanakya/classroom.jpg"
              alt="Chanakya University modern classroom"
              className="h-44 w-full object-cover"
            />
            <div className="p-5 space-y-2 flex-1">
              <div className="gold-badge">Shared Library</div>
              <h3 className="text-base font-semibold text-[#142B4A]">Discover & save key papers</h3>
              <p className="text-xs text-[#697386] leading-relaxed">
                Search scholarly literature, build personal reading collections with private notes, and see what colleagues recommend.
              </p>
            </div>
          </Link>

          <Link to="/researchers" className="surface-card-interactive overflow-hidden flex flex-col">
            <img
              src="/images/chanakya/Sports.jpg"
              alt="Chanakya University campus life"
              className="h-44 w-full object-cover"
            />
            <div className="p-5 space-y-2 flex-1">
              <div className="sage-badge">Campus Network</div>
              <h3 className="text-base font-semibold text-[#142B4A]">Meet people across departments</h3>
              <p className="text-xs text-[#697386] leading-relaxed">
                Connect with students, mentors, and researchers exploring complementary questions beyond your own classroom.
              </p>
            </div>
          </Link>
        </div>
      </section>

      {/* Explore by School / Department */}
      {departments.length > 0 && (
        <section className="bg-white border-y border-[#E6E2D8]">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 space-y-7">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
              <div>
                <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">
                  Explore research across departments
                </h2>
                <p className="text-sm text-[#697386] mt-1">
                  Browse active topics, publications, and colleagues by academic area.
                </p>
              </div>
              <Link to="/discover" className="text-sm font-medium text-[#142B4A] hover:text-[#8E6914] inline-flex items-center gap-1">
                Explore all areas <ArrowRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {departments.map((d) => (
                <Link
                  key={d.code}
                  to={`/discover?department=${encodeURIComponent(d.code)}`}
                  className="surface-card-interactive p-5 flex flex-col justify-between gap-3 bg-[#FAF8F2]/50 hover:bg-white"
                >
                  <div>
                    <div className="text-[11px] font-semibold tracking-wider uppercase text-[#8E6914]">
                      {d.code}
                    </div>
                    <h3 className="text-sm font-semibold text-[#142B4A] mt-1">{d.name}</h3>
                    <p className="text-xs text-[#697386] mt-1.5 line-clamp-2 leading-relaxed">
                      {d.description}
                    </p>
                  </div>
                  <div className="text-xs text-[#697386] pt-2.5 border-t border-[#EFECE4] flex items-center justify-between">
                    <span>{d.member_count} campus members</span>
                    <span className="text-[#142B4A] font-medium">Explore →</span>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Popular in the University Library */}
      {featuredPapers.length > 0 && (
        <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">
                Papers students and faculty are reading
              </h2>
              <p className="text-sm text-[#697386] mt-1">
                Popular publications saved in the shared Chanakya University library.
              </p>
            </div>
            <Link to="/library" className="text-sm font-medium text-[#142B4A] hover:text-[#8E6914] inline-flex items-center gap-1">
              Open library <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            {featuredPapers.map((p) => (
              <PaperCard key={p.id} paper={p} />
            ))}
          </div>
        </section>
      )}

      {/* People to Connect With + Closing Invite */}
      {researchers.length > 0 && (
        <section className="bg-white border-t border-[#E6E2D8]">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 space-y-10">
            <div className="space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
                <div>
                  <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">
                    Connect with fellow researchers
                  </h2>
                  <p className="text-sm text-[#697386] mt-1">
                    Meet faculty mentors, researchers, and peers working on ideas you care about.
                  </p>
                </div>
                <Link to="/researchers" className="text-sm font-medium text-[#142B4A] hover:text-[#8E6914] inline-flex items-center gap-1">
                  View directory <ArrowRight className="h-4 w-4" />
                </Link>
              </div>

              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {researchers.map((r) => (
                  <Link key={r.id} to={`/researchers/${r.id}`} className="surface-card-interactive p-5 space-y-3">
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-full bg-[#142B4A] text-[#FBF5E4] flex items-center justify-center text-xs font-semibold shrink-0">
                        {getInitials(r.full_name)}
                      </div>
                      <div className="min-w-0">
                        <div className="text-sm font-semibold text-[#142B4A] truncate">{r.full_name}</div>
                        <div className="text-xs text-[#697386] capitalize truncate">
                          {r.role} · {r.department_code}
                        </div>
                      </div>
                    </div>
                    <p className="text-xs text-[#697386] line-clamp-2 leading-relaxed">
                      {r.research_interests_text || r.bio}
                    </p>
                  </Link>
                ))}
              </div>
            </div>

            {/* Warm Architectural Closing Banner */}
            <div className="rounded-2xl overflow-hidden border border-[#E6E2D8] bg-[#142B4A] text-white grid md:grid-cols-12 items-center">
              <div className="md:col-span-7 p-8 sm:p-10 space-y-4">
                <h3 className="text-2xl font-semibold leading-snug">
                  Ready to join your campus research community?
                </h3>
                <p className="text-sm text-slate-300 leading-relaxed">
                  Share what you are exploring, save papers for your courses and projects, and connect with mentors and classmates across Chanakya University.
                </p>
                <div className="flex flex-wrap gap-3 pt-1">
                  <Link to="/register" className="btn-gold py-2.5 px-5">
                    Create Your Profile
                  </Link>
                  <Link
                    to="/login"
                    className="inline-flex items-center justify-center rounded-lg border border-white/25 px-5 py-2.5 text-sm font-medium text-white hover:bg-white/10 transition-colors"
                  >
                    Sign In
                  </Link>
                </div>
              </div>
              <div className="md:col-span-5 h-full min-h-[220px]">
                <img
                  src="/images/chanakya/CU-logo.jpg"
                  alt="Chanakya University Administration Block"
                  className="w-full h-full object-cover"
                />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Footer */}
      <footer className="bg-[#FAF8F2] border-t border-[#E6E2D8] mt-auto">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#697386]">
          <BrandLogo />
          <div className="flex flex-wrap items-center gap-5">
            <Link to="/discussions" className="hover:text-[#142B4A]">Community</Link>
            <Link to="/discover" className="hover:text-[#142B4A]">Explore</Link>
            <Link to="/search" className="hover:text-[#142B4A]">Research</Link>
            <Link to="/library" className="hover:text-[#142B4A]">Library</Link>
            <Link to="/assistant" className="hover:text-[#142B4A]">Research Assistant</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
