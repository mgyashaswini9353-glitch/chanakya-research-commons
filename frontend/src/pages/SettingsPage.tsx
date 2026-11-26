import React, { useEffect, useState } from 'react';
import { Save, X } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { formatTopicLabel } from '../components/UIPrimitives';

export default function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const { showToast } = useToast();
  const [departments, setDepartments] = useState<any[]>([]);
  const [form, setForm] = useState({
    full_name: '',
    department_id: '',
    bio: '',
    research_interests_text: '',
    tags_str: '',
    pubs_str: '',
    personal_website: '',
  });
  const [followedTopics, setFollowedTopics] = useState<string[]>([]);
  const [newTopic, setNewTopic] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/api/departments').then(setDepartments).catch(() => {});
    api.get('/api/users/me/topics').then(setFollowedTopics).catch(() => {});
  }, []);

  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name || '',
        department_id: user.department_id ? String(user.department_id) : '',
        bio: user.bio || '',
        research_interests_text: user.research_interests_text || '',
        tags_str: (user.research_tags || []).map(formatTopicLabel).join(', '),
        pubs_str: (user.publication_links || []).join('\n'),
        personal_website: user.personal_website || '',
      });
    }
  }, [user]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.patch('/api/users/me', {
        full_name: form.full_name.trim(),
        department_id: form.department_id ? Number(form.department_id) : null,
        bio: form.bio.trim(),
        research_interests_text: form.research_interests_text.trim(),
        research_tags: form.tags_str
          .split(',')
          .map((t) => t.trim().toLowerCase().replace(/\s+/g, '-'))
          .filter(Boolean),
        publication_links: form.pubs_str.split('\n').map((l) => l.trim()).filter(Boolean),
        personal_website: form.personal_website.trim(),
      });
      await refreshUser();
      showToast('Profile settings updated');
    } catch (err: any) {
      showToast(err.message || 'Could not save settings', 'error');
    } finally {
      setSaving(false);
    }
  };

  const addTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTopic.trim()) return;
    const t = newTopic.trim().toLowerCase().replace(/\s+/g, '-');
    await api.post('/api/users/me/topics/follow', { topic: t });
    setFollowedTopics((p) => Array.from(new Set([...p, t])));
    setNewTopic('');
    showToast(`Following ${formatTopicLabel(t)}`);
  };

  const removeTopic = async (t: string) => {
    await api.del(`/api/users/me/topics/follow/${encodeURIComponent(t)}`);
    setFollowedTopics((p) => p.filter((x) => x !== t));
    showToast(`Unfollowed ${formatTopicLabel(t)}`, 'info');
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Account & Profile Settings</h1>
        <p className="text-sm text-[#697386] mt-0.5">
          Keep your profile and research areas current to receive relevant publication and researcher suggestions.
        </p>
      </div>

      <form onSubmit={handleSave} className="surface-card p-6 space-y-4">
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Full name</label>
            <input value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} className="input-field" />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Department</label>
            <select value={form.department_id} onChange={(e) => setForm({ ...form, department_id: e.target.value })} className="input-field bg-white">
              {departments.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">Academic biography</label>
          <textarea rows={2} value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="input-field" />
        </div>

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">Research interests</label>
          <textarea rows={3} value={form.research_interests_text} onChange={(e) => setForm({ ...form, research_interests_text: e.target.value })} className="input-field" />
        </div>

        <div>
          <label className="block text-xs font-medium text-[#263247] mb-1">Research topics (comma separated)</label>
          <input value={form.tags_str} onChange={(e) => setForm({ ...form, tags_str: e.target.value })} className="input-field" />
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Personal website or lab page</label>
            <input value={form.personal_website} onChange={(e) => setForm({ ...form, personal_website: e.target.value })} className="input-field text-xs" />
          </div>
          <div>
            <label className="block text-xs font-medium text-[#263247] mb-1">Publication profile links (one per line)</label>
            <textarea rows={2} value={form.pubs_str} onChange={(e) => setForm({ ...form, pubs_str: e.target.value })} className="input-field text-xs" />
          </div>
        </div>

        <div className="pt-2">
          <button type="submit" disabled={saving} className="btn-primary text-xs">
            <Save className="h-3.5 w-3.5" /> {saving ? 'Saving...' : 'Save Profile'}
          </button>
        </div>
      </form>

      <div className="surface-card p-6 space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-[#142B4A]">Followed Research Topics</h2>
          <p className="text-xs text-[#697386] mt-0.5">Topics you follow shape your personalized Home feed and reading suggestions.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {followedTopics.map((t) => (
            <span key={t} className="inline-flex items-center gap-1.5 rounded-full bg-[#E9EFE8] border border-[#CFE0CC] px-3 py-1 text-xs font-medium text-[#2E5438]">
              {formatTopicLabel(t)}
              <button onClick={() => removeTopic(t)} className="hover:text-rose-600" aria-label={`Unfollow ${t}`}>
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
        <form onSubmit={addTopic} className="flex gap-2 max-w-md">
          <input
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            placeholder="Follow a topic (e.g. Solid State Batteries)..."
            className="input-field text-xs py-1.5"
          />
          <button type="submit" className="btn-secondary text-xs py-1.5 shrink-0">Follow</button>
        </form>
      </div>
    </div>
  );
}
