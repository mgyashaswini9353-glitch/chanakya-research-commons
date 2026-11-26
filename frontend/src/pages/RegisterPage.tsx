import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Check, Eye, EyeOff, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { BrandLogo } from '../components/BrandLogo';

export default function RegisterPage() {
  const { register } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [departments, setDepartments] = useState<any[]>([]);
  const [showPassword, setShowPassword] = useState(false);
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    username: '',
    password: '',
    role: 'student',
    department_id: '',
    research_interests_text: '',
    tags_input: '',
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .get('/api/departments')
      .then((d) => {
        setDepartments(d || []);
        if (d?.length > 0) setForm((f) => ({ ...f, department_id: String(d[0].id) }));
      })
      .catch(() => {});
  }, []);

  const hasMinLen = form.password.length >= 6;
  const hasLetter = /[a-zA-Z]/.test(form.password);
  const hasDigit = /\d/.test(form.password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.full_name.trim() || !form.email.trim()) {
      setError('Please complete all required fields.');
      return;
    }
    if (!hasMinLen) {
      setError('Password must be at least 6 characters long.');
      return;
    }
    const derivedUsername =
      form.username.trim() ||
      form.email.split('@')[0].replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase();

    setLoading(true);
    try {
      const tags = form.tags_input
        .split(',')
        .map((t) => t.trim().toLowerCase().replace(/\s+/g, '-'))
        .filter(Boolean);

      await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        username: derivedUsername,
        password: form.password,
        role: form.role,
        department_id: form.department_id ? Number(form.department_id) : null,
        research_interests_text: form.research_interests_text.trim(),
        research_tags: tags,
      });
      showToast('Welcome to Chanakya Research Commons!');
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Unable to create account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F2] grid lg:grid-cols-2">
      {/* Left Campus Photo Panel */}
      <div className="hidden lg:flex relative flex-col justify-between p-12 text-white overflow-hidden">
        <img
          src="/images/chanakya/CU-New-Campus-Infra_246.jpg"
          alt="Chanakya University campus learning spaces"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-[#142B4A]/82" />

        <div className="relative z-10">
          <Link to="/">
            <BrandLogo onDark />
          </Link>
        </div>

        <div className="relative z-10 max-w-md space-y-4">
          <div className="h-1 w-12 bg-[#D6AA35] rounded-full" />
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Be part of the conversations shaping tomorrow.
          </h1>
          <p className="text-sm text-slate-200 leading-relaxed">
            Create your Chanakya University profile to connect with peers and faculty, save helpful papers, and share what you are building.
          </p>
        </div>

        <div className="relative z-10 text-xs text-slate-300">
          Chanakya University · Research Commons
        </div>
      </div>

      {/* Right Registration Form */}
      <div className="flex flex-col justify-center items-center p-6 sm:p-10">
        <div className="w-full max-w-lg space-y-5">
          <div className="lg:hidden">
            <Link to="/">
              <BrandLogo />
            </Link>
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Join the campus community</h2>
            <p className="text-sm text-[#697386]">Set up your academic profile in under a minute.</p>
          </div>

          <form onSubmit={handleSubmit} className="surface-card p-6 sm:p-7 space-y-4">
            {error && (
              <div role="alert" className="rounded-lg bg-rose-50 border border-rose-200 px-3.5 py-2.5 text-xs text-rose-800">
                {error}
              </div>
            )}

            <div className="grid sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Full name *</label>
                <input
                  required
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="Ananya Rao"
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">University email *</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="ananya@chanakya.edu.in"
                  className="input-field"
                />
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Username</label>
                <input
                  value={form.username}
                  onChange={(e) => setForm({ ...form, username: e.target.value })}
                  placeholder="Optional"
                  className="input-field"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Password *</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    minLength={6}
                    value={form.password}
                    onChange={(e) => setForm({ ...form, password: e.target.value })}
                    placeholder="At least 6 characters"
                    className="input-field pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8A92A0] hover:text-[#142B4A]"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 text-[11px]">
              <span className={`inline-flex items-center gap-1 ${hasMinLen ? 'text-[#2E5438]' : 'text-[#8A92A0]'}`}>
                <Check className="h-3 w-3" /> 6+ characters
              </span>
              <span className={`inline-flex items-center gap-1 ${hasLetter ? 'text-[#2E5438]' : 'text-[#8A92A0]'}`}>
                <Check className="h-3 w-3" /> Letters
              </span>
              <span className={`inline-flex items-center gap-1 ${hasDigit ? 'text-[#2E5438]' : 'text-[#8A92A0]'}`}>
                <Check className="h-3 w-3" /> Number
              </span>
            </div>

            <div className="grid sm:grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Role</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="input-field bg-white"
                >
                  <option value="student">Student</option>
                  <option value="faculty">Faculty</option>
                  <option value="researcher">Researcher</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#263247] mb-1">Department</label>
                <select
                  value={form.department_id}
                  onChange={(e) => setForm({ ...form, department_id: e.target.value })}
                  className="input-field bg-white"
                >
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-[#263247] mb-1">What are you curious about?</label>
              <textarea
                rows={2}
                value={form.research_interests_text}
                onChange={(e) => setForm({ ...form, research_interests_text: e.target.value })}
                placeholder="Share the projects, topics, or research areas you enjoy..."
                className="input-field"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-[#263247] mb-1">Areas of interest (comma separated)</label>
              <input
                value={form.tags_input}
                onChange={(e) => setForm({ ...form, tags_input: e.target.value })}
                placeholder="Machine Learning, Sustainability, Genomics"
                className="input-field"
              />
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? 'Creating profile...' : 'Create Profile'}
            </button>
          </form>

          <p className="text-center text-sm text-[#697386]">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-[#142B4A] underline decoration-[#D6AA35] underline-offset-2">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
