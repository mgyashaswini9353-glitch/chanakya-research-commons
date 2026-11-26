import React, { createContext, useContext, useEffect, useState } from 'react';
import { api, getToken, setToken } from '../services/api';

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  full_name: string;
  role: 'student' | 'faculty' | 'researcher' | 'admin';
  department_id?: number;
  department_code?: string;
  department_name?: string;
  bio: string;
  research_interests_text: string;
  research_tags: string[];
  publication_links: string[];
  personal_website: string;
  followers_count?: number;
  following_count?: number;
  posts_count?: number;
  saved_papers_count?: number;
  followed_topics?: string[];
}

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<UserProfile>;
  register: (payload: any) => Promise<UserProfile>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.get<UserProfile>('/api/auth/me');
      setUser(me);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; user: UserProfile }>('/api/auth/login', {
      email,
      password,
    });
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const register = async (payload: any) => {
    const res = await api.post<{ access_token: string; user: UserProfile }>('/api/auth/register', payload);
    setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    api.post('/api/auth/logout').catch(() => {});
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
