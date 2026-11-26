import React, { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Bell,
  BookMarked,
  ChevronDown,
  Compass,
  FolderOpen,
  Home,
  LogOut,
  Menu,
  MessageSquare,
  Search,
  Settings,
  Shield,
  Sparkles,
  TrendingUp,
  User as UserIcon,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { BrandLogo } from '../components/BrandLogo';
import { formatRelativeDate, getInitials } from '../components/UIPrimitives';

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [quickQuery, setQuickQuery] = useState('');
  const [mobileOpen, setMobileOpen] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notifications, setNotifications] = useState<any[]>([]);

  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!user) {
      setNotifications([]);
      return;
    }
    api
      .get('/api/notifications?limit=10')
      .then((res) => setNotifications(res.items || []))
      .catch(() => {});
  }, [user]);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setNotifOpen(false);
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) setProfileOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const handleGlobalSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = quickQuery.trim();
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/search');
    setMobileOpen(false);
  };

  // Clean 5-item Chanakya University navigation
  const primaryNav = [
    { to: '/dashboard', label: 'Home', icon: Home },
    { to: '/discussions', label: 'Community', icon: MessageSquare },
    { to: '/discover', label: 'Explore', icon: Compass },
    { to: '/search', label: 'Research', icon: Search },
    { to: '/library', label: 'My Library', icon: BookMarked },
  ];

  const firstDisplayName = user
    ? user.full_name.replace(/^Dr\.\s+/i, '').split(' ')[0]
    : '';

  return (
    <div className="min-h-screen flex flex-col bg-[#FAF8F2]">
      {/* Subtle Chanakya Gold accent bar */}
      <div className="h-[3px] bg-[#D6AA35] w-full" />

      {/* Clean White / Ivory Header */}
      <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-[#E6E2D8]">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Official Chanakya University Logo */}
          <Link to={user ? '/dashboard' : '/'} className="shrink-0">
            <BrandLogo />
          </Link>

          {/* Simple Primary Navigation */}
          <nav className="hidden lg:flex items-center h-full gap-1" aria-label="Main navigation">
            {primaryNav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `h-full inline-flex items-center gap-1.5 px-3 text-[13.5px] font-medium border-b-2 whitespace-nowrap transition-colors ${
                      isActive
                        ? 'border-[#D6AA35] text-[#142B4A]'
                        : 'border-transparent text-[#697386] hover:text-[#142B4A]'
                    }`
                  }
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Compact Search + Notifications + Profile */}
          <div className="flex items-center gap-2.5">
            <form onSubmit={handleGlobalSearch} className="relative hidden md:block w-52 xl:w-64">
              <Search className="h-4 w-4 text-[#8A92A0] absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="search"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="Search campus research..."
                aria-label="Search research"
                className="w-full rounded-full border border-[#E6E2D8] bg-[#FAF8F2] pl-9 pr-3.5 py-1.5 text-xs text-[#263247] placeholder-[#8A92A0] focus:bg-white focus:border-[#142B4A] focus:outline-none focus:ring-2 focus:ring-[#D6AA35]/25 transition-colors"
              />
            </form>

            {user ? (
              <>
                {/* Notifications Bell */}
                <div className="relative" ref={notifRef}>
                  <button
                    onClick={() => {
                      setNotifOpen((o) => !o);
                      setProfileOpen(false);
                    }}
                    aria-label="Notifications"
                    className="relative rounded-full p-2 text-[#697386] hover:bg-[#F3F4F2] hover:text-[#142B4A] transition-colors"
                  >
                    <Bell className="h-4 w-4" />
                    {notifications.length > 0 && (
                      <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[#D6AA35]" />
                    )}
                  </button>

                  {notifOpen && (
                    <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl border border-[#E6E2D8] bg-white shadow-dropdown overflow-hidden z-50">
                      <div className="px-4 py-3 border-b border-[#F0ECE2] flex items-center justify-between bg-[#FAF8F2]">
                        <span className="text-xs font-semibold text-[#142B4A]">Notifications</span>
                        <span className="text-[11px] text-[#697386]">{notifications.length} recent</span>
                      </div>
                      <div className="max-h-80 overflow-y-auto divide-y divide-[#F3F0E8]">
                        {notifications.length === 0 ? (
                          <div className="p-6 text-center text-xs text-[#697386]">
                            You are all caught up.
                          </div>
                        ) : (
                          notifications.map((n) => (
                            <Link
                              key={n.id}
                              to={n.link || '/dashboard'}
                              onClick={() => setNotifOpen(false)}
                              className="block px-4 py-3 hover:bg-[#FAF8F2] transition-colors"
                            >
                              <div className="text-xs font-medium text-[#263247]">{n.title}</div>
                              <div className="text-[11px] text-[#697386] mt-0.5 flex items-center justify-between gap-2">
                                <span className="truncate">{n.subtitle}</span>
                                {n.created_at && (
                                  <span className="shrink-0 text-[10px] text-[#8A92A0]">
                                    {formatRelativeDate(n.created_at)}
                                  </span>
                                )}
                              </div>
                            </Link>
                          ))
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* User Profile Menu */}
                <div className="relative" ref={profileRef}>
                  <button
                    onClick={() => {
                      setProfileOpen((o) => !o);
                      setNotifOpen(false);
                    }}
                    className="inline-flex items-center gap-2 rounded-full border border-[#E6E2D8] bg-white pl-1.5 pr-3 py-1 hover:bg-[#FAF8F2] transition-colors"
                  >
                    <div className="h-7 w-7 rounded-full bg-[#142B4A] text-[#FBF5E4] flex items-center justify-center text-[11px] font-semibold">
                      {getInitials(user.full_name)}
                    </div>
                    <span className="hidden sm:inline text-xs font-medium text-[#263247] max-w-[100px] truncate">
                      {firstDisplayName}
                    </span>
                    <ChevronDown className="h-3.5 w-3.5 text-[#697386]" />
                  </button>

                  {profileOpen && (
                    <div className="absolute right-0 mt-2 w-60 rounded-xl border border-[#E6E2D8] bg-white shadow-dropdown py-1.5 z-50">
                      <div className="px-4 py-2.5 border-b border-[#F0ECE2]">
                        <div className="text-xs font-semibold text-[#142B4A] truncate">{user.full_name}</div>
                        <div className="text-[11px] text-[#697386] capitalize truncate">
                          {user.role} · {user.department_name || user.department_code || 'Chanakya University'}
                        </div>
                      </div>

                      <div className="py-1">
                        <Link
                          to={`/researchers/${user.id}`}
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <UserIcon className="h-3.5 w-3.5 text-[#697386]" /> My Profile
                        </Link>
                        <Link
                          to="/researchers"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <Users className="h-3.5 w-3.5 text-[#697386]" /> People Directory
                        </Link>
                        <Link
                          to="/recommendations"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <Sparkles className="h-3.5 w-3.5 text-[#A67E1E]" /> Recommended for You
                        </Link>
                        <Link
                          to="/assistant"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <Sparkles className="h-3.5 w-3.5 text-[#142B4A]" /> Research Assistant
                        </Link>
                        <Link
                          to="/trends"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <TrendingUp className="h-3.5 w-3.5 text-[#697386]" /> Research Trends
                        </Link>
                        <Link
                          to="/collections"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <FolderOpen className="h-3.5 w-3.5 text-[#697386]" /> My Collections
                        </Link>
                        <Link
                          to="/settings"
                          onClick={() => setProfileOpen(false)}
                          className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#263247] hover:bg-[#FAF8F2]"
                        >
                          <Settings className="h-3.5 w-3.5 text-[#697386]" /> Account Settings
                        </Link>
                      </div>

                      {user.role === 'admin' && (
                        <div className="border-t border-[#F0ECE2] py-1">
                          <div className="px-4 py-1 text-[10px] font-semibold uppercase tracking-wider text-[#8A92A0]">
                            University Administration
                          </div>
                          <Link
                            to="/analytics"
                            onClick={() => setProfileOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#142B4A] font-medium hover:bg-[#FAF8F2]"
                          >
                            <BarChart3 className="h-3.5 w-3.5 text-[#A67E1E]" /> Institutional Insights
                          </Link>
                          <Link
                            to="/admin"
                            onClick={() => setProfileOpen(false)}
                            className="flex items-center gap-2.5 px-4 py-2 text-xs text-[#142B4A] font-medium hover:bg-[#FAF8F2]"
                          >
                            <Shield className="h-3.5 w-3.5 text-[#697386]" /> Administration
                          </Link>
                        </div>
                      )}

                      <div className="border-t border-[#F0ECE2] pt-1">
                        <button
                          onClick={() => {
                            setProfileOpen(false);
                            logout();
                            navigate('/login');
                          }}
                          className="w-full flex items-center gap-2.5 px-4 py-2 text-xs text-rose-700 hover:bg-rose-50"
                        >
                          <LogOut className="h-3.5 w-3.5" /> Sign Out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="btn-ghost text-xs">
                  Sign in
                </Link>
                <Link to="/register" className="btn-primary text-xs py-1.5 px-3.5">
                  Join Community
                </Link>
              </div>
            )}

            <button
              onClick={() => setMobileOpen((o) => !o)}
              aria-label="Toggle menu"
              className="lg:hidden rounded-lg p-2 text-[#697386] hover:bg-[#F3F4F2]"
            >
              {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer */}
        {mobileOpen && (
          <div className="lg:hidden border-t border-[#E6E2D8] bg-white px-4 py-3 space-y-3">
            <form onSubmit={handleGlobalSearch} className="relative">
              <Search className="h-4 w-4 text-[#8A92A0] absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="search"
                value={quickQuery}
                onChange={(e) => setQuickQuery(e.target.value)}
                placeholder="Search campus research..."
                className="input-field pl-9 py-2 text-sm"
              />
            </form>
            <div className="grid grid-cols-2 gap-1.5">
              {primaryNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setMobileOpen(false)}
                    className={({ isActive }) =>
                      `flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium ${
                        isActive ? 'bg-[#FBF5E4] text-[#142B4A]' : 'text-[#263247] hover:bg-[#FAF8F2]'
                      }`
                    }
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </NavLink>
                );
              })}
              <NavLink
                to="/researchers"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#263247] hover:bg-[#FAF8F2]"
              >
                <Users className="h-4 w-4" /> People
              </NavLink>
              <NavLink
                to="/assistant"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#263247] hover:bg-[#FAF8F2]"
              >
                <Sparkles className="h-4 w-4" /> Assistant
              </NavLink>
              <NavLink
                to="/trends"
                onClick={() => setMobileOpen(false)}
                className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-[#263247] hover:bg-[#FAF8F2]"
              >
                <TrendingUp className="h-4 w-4" /> Trends
              </NavLink>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-[1280px] w-full mx-auto px-4 sm:px-6 py-6">
        <Outlet />
      </main>

      {/* Warm Chanakya University Footer */}
      <footer className="border-t border-[#E6E2D8] bg-white mt-14">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#697386]">
          <div className="flex items-center gap-3">
            <img
              src="/images/chanakya/chanakya-logo-official.png"
              alt="Chanakya University"
              className="h-7 w-auto object-contain"
            />
            <span className="border-l border-[#E6E2D8] pl-3">
              Research Commons · Ideas grow when we share them.
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-5">
            <Link to="/discussions" className="hover:text-[#142B4A]">Community</Link>
            <Link to="/discover" className="hover:text-[#142B4A]">Explore</Link>
            <Link to="/search" className="hover:text-[#142B4A]">Research</Link>
            <Link to="/researchers" className="hover:text-[#142B4A]">People</Link>
            <Link to="/assistant" className="hover:text-[#142B4A]">Assistant</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
