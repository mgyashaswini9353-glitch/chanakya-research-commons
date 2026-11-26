import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, UserCheck, UserPlus, Users } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { CardSkeleton, EmptyState, formatTopicLabel, getInitials } from '../components/UIPrimitives';

export default function ResearchersPage() {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [users, setUsers] = useState<any[]>([]);
  const [departments, setDepartments] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [dept, setDept] = useState('');
  const [role, setRole] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/departments').then(setDepartments).catch(() => {});
  }, []);

  const load = () => {
    setLoading(true);
    const params = new URLSearchParams();
    if (q.trim()) params.set('q', q.trim());
    if (dept) params.set('department_code', dept);
    if (role) params.set('role', role);
    api
      .get(`/api/users?${params.toString()}`)
      .then((res) => setUsers(res || []))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dept, role]);

  const toggleFollow = async (target: any) => {
    if (!user) return;
    try {
      if (target.is_following) {
        await api.del(`/api/users/${target.id}/follow`);
        showToast(`Unfollowed ${target.full_name}`, 'info');
      } else {
        await api.post(`/api/users/${target.id}/follow`);
        showToast(`Now following ${target.full_name}`);
      }
      setUsers((prev) =>
        prev.map((u) =>
          u.id === target.id
            ? {
                ...u,
                is_following: !u.is_following,
                followers_count: (u.followers_count || 0) + (u.is_following ? -1 : 1),
              }
            : u
        )
      );
    } catch (err: any) {
      showToast(err.message || 'Could not update follow status', 'error');
    }
  };

  return (
    <div className="space-y-6">
      <div className="surface-card p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Researchers Directory</h1>
            <p className="text-sm text-[#697386] mt-0.5">
              Connect with faculty, postdoctoral researchers, and students across university departments.
            </p>
          </div>
          <span className="text-xs font-medium text-[#697386]">{users.length} members</span>
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            load();
          }}
          className="flex flex-col md:flex-row gap-2.5"
        >
          <div className="relative flex-1">
            <Search className="h-4 w-4 text-[#8A92A0] absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search by name, research area, or topic..."
              className="input-field pl-9"
            />
          </div>
          <select
            value={dept}
            onChange={(e) => setDept(e.target.value)}
            className="input-field md:w-56 bg-white"
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d.code} value={d.code}>{d.name}</option>
            ))}
          </select>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="input-field md:w-40 bg-white"
          >
            <option value="">All Roles</option>
            <option value="faculty">Faculty</option>
            <option value="researcher">Researcher</option>
            <option value="student">Student</option>
          </select>
          <button type="submit" className="btn-primary px-5">Filter</button>
        </form>
      </div>

      {loading ? (
        <CardSkeleton rows={4} />
      ) : users.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No researchers matched your filters"
          description="Try clearing your search or selecting a different department."
        />
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {users.map((u) => (
            <div key={u.id} className="surface-card-interactive p-5 flex flex-col justify-between gap-4">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-11 w-11 rounded-full bg-[#142B4A] text-white flex items-center justify-center text-xs font-semibold shrink-0">
                      {getInitials(u.full_name)}
                    </div>
                    <div className="min-w-0">
                      <Link
                        to={`/researchers/${u.id}`}
                        className="text-sm font-semibold text-[#142B4A] hover:text-[#8E6914] truncate block"
                      >
                        {u.full_name}
                      </Link>
                      <div className="text-xs text-[#697386] capitalize truncate">
                        {u.role} · {u.department_name || u.department_code}
                      </div>
                    </div>
                  </div>
                  {user && user.id !== u.id && (
                    <button
                      onClick={() => toggleFollow(u)}
                      className={`shrink-0 inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-medium border transition-colors ${
                        u.is_following
                          ? 'bg-[#E9EFE8] border-[#CFE0CC] text-[#2E5438]'
                          : 'bg-white border-[#DCD7CA] text-[#142B4A] hover:bg-[#FAF8F2]'
                      }`}
                    >
                      {u.is_following ? <UserCheck className="h-3.5 w-3.5" /> : <UserPlus className="h-3.5 w-3.5" />}
                      {u.is_following ? 'Following' : 'Follow'}
                    </button>
                  )}
                </div>

                <p className="text-xs text-[#4A5568] leading-relaxed line-clamp-2">
                  {u.research_interests_text || u.bio || 'Active member of Chanakya Research Commons.'}
                </p>

                <div className="flex flex-wrap gap-1.5">
                  {(u.research_tags || []).slice(0, 3).map((t: string) => (
                    <span key={t} className="topic-pill">{formatTopicLabel(t)}</span>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-[#697386] pt-3 border-t border-[#F0ECE2]">
                <span>{u.followers_count || 0} followers · {u.saved_papers_count || 0} saved</span>
                <Link to={`/researchers/${u.id}`} className="font-medium text-[#8E6914] hover:underline">
                  View profile
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
