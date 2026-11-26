import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, Eye, EyeOff, Loader2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { BrandLogo } from '../components/BrandLogo';

const DEMO_ACCOUNTS = [
  { role: 'Student', email: 'student@chanakya.edu.in', area: 'Data Science & Engineering' },
  { role: 'Faculty', email: 'faculty@chanakya.edu.in', area: 'Computer Science & AI' },
  { role: 'Researcher', email: 'researcher@chanakya.edu.in', area: 'Biotechnology & Bioinformatics' },
  { role: 'Administrator', email: 'admin@chanakya.edu.in', area: 'University Insights' },
];

export default function LoginPage() {
  const { login } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const performLogin = async (ident: string, pwd: string) => {
    setError('');
    if (!ident.trim() || !pwd) {
      setError('Please enter both your university email and password.');
      return;
    }
    setLoading(true);
    try {
      const user = await login(ident.trim(), pwd);
      showToast(`Welcome back, ${user.full_name}`);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Unable to sign in. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAF8F2] grid lg:grid-cols-2">
      {/* Left Campus Photography Panel */}
      <div className="hidden lg:flex relative flex-col justify-between p-12 text-white overflow-hidden">
        <img
          src="/images/chanakya/campus.jpg"
          alt="Chanakya University Campus"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-[#142B4A]/80" />

        <div className="relative z-10">
          <Link to="/">
            <BrandLogo onDark />
          </Link>
        </div>

        <div className="relative z-10 max-w-md space-y-4">
          <div className="h-1 w-12 bg-[#D6AA35] rounded-full" />
          <h1 className="text-3xl font-semibold leading-tight tracking-tight">
            Ideas grow when we share them.
          </h1>
          <p className="text-sm text-slate-200 leading-relaxed">
            Sign in to share what you are working on, organize readings in your personal library, and connect with faculty and peers across Chanakya University.
          </p>
        </div>

        <div className="relative z-10 text-xs text-slate-300">
          Chanakya University · Bengaluru
        </div>
      </div>

      {/* Right Sign-in Form */}
      <div className="flex flex-col justify-center items-center p-6 sm:p-10">
        <div className="w-full max-w-md space-y-6">
          <div className="lg:hidden">
            <Link to="/">
              <BrandLogo />
            </Link>
          </div>

          <div className="space-y-1">
            <h2 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Welcome back</h2>
            <p className="text-sm text-[#697386]">
              Sign in with your Chanakya University email or username.
            </p>
          </div>

          <div className="surface-card p-6 sm:p-7 space-y-5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                performLogin(email, password);
              }}
              className="space-y-4"
              noValidate
            >
              {error && (
                <div role="alert" className="rounded-lg bg-rose-50 border border-rose-200 px-3.5 py-2.5 text-xs text-rose-800">
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="login-email" className="block text-xs font-medium text-[#263247] mb-1.5">
                  University email or username
                </label>
                <input
                  id="login-email"
                  type="text"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@chanakya.edu.in"
                  className="input-field"
                />
              </div>

              <div>
                <label htmlFor="login-password" className="block text-xs font-medium text-[#263247] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    className="input-field pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((s) => !s)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8A92A0] hover:text-[#142B4A]"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <button type="submit" disabled={loading} className="btn-primary w-full py-2.5">
                {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {/* Discreet Sample Account Access */}
            <div className="border-t border-[#EFECE4] pt-4">
              <button
                type="button"
                onClick={() => setShowDemo((v) => !v)}
                className="w-full flex items-center justify-between text-xs font-medium text-[#697386] hover:text-[#142B4A]"
              >
                <span>Quick sign-in with sample member accounts</span>
                {showDemo ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>

              {showDemo && (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {DEMO_ACCOUNTS.map((acc) => (
                    <button
                      key={acc.email}
                      type="button"
                      disabled={loading}
                      onClick={() => performLogin(acc.email, 'Chanakya@2026')}
                      className="text-left rounded-lg border border-[#E6E2D8] bg-[#FAF8F2] hover:border-[#D6AA35] hover:bg-[#FBF5E4]/60 p-2.5 transition-colors"
                    >
                      <div className="text-xs font-semibold text-[#142B4A]">{acc.role}</div>
                      <div className="text-[11px] text-[#697386] truncate">{acc.area}</div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          <p className="text-center text-sm text-[#697386]">
            New to Chanakya Research Commons?{' '}
            <Link to="/register" className="font-medium text-[#142B4A] underline decoration-[#D6AA35] underline-offset-2">
              Create your account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
