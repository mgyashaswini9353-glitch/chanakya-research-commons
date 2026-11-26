import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Edit2, FolderOpen, FolderPlus, Save, Trash2 } from 'lucide-react';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';
import { CardSkeleton, ConfirmDialog, EmptyState } from '../components/UIPrimitives';

export default function CollectionsPage() {
  const { showToast } = useToast();
  const [collections, setCollections] = useState<any[]>([]);
  const [selectedColId, setSelectedColId] = useState<number | null>(null);
  const [items, setItems] = useState<any[]>([]);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameDraft, setRenameDraft] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<any>(null);
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [noteDraft, setNoteDraft] = useState('');
  const [loading, setLoading] = useState(true);

  const loadAll = async (colId: number | null = selectedColId) => {
    setLoading(true);
    try {
      const [cols, myLib] = await Promise.all([
        api.get('/api/collections'),
        api.get(colId ? `/api/library/my?collection_id=${colId}` : '/api/library/my'),
      ]);
      setCollections(cols || []);
      setItems(myLib.items || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll(selectedColId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedColId]);

  const createCol = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    await api.post('/api/collections', { name: newName.trim(), description: newDesc.trim(), is_private: true });
    setNewName('');
    setNewDesc('');
    showToast('Collection created');
    loadAll(selectedColId);
  };

  const saveRename = async (id: number) => {
    if (!renameDraft.trim()) return;
    await api.patch(`/api/collections/${id}`, { name: renameDraft.trim() });
    setRenamingId(null);
    showToast('Collection renamed');
    loadAll(selectedColId);
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    await api.del(`/api/collections/${deleteTarget.id}`);
    if (selectedColId === deleteTarget.id) setSelectedColId(null);
    setDeleteTarget(null);
    showToast('Collection removed', 'info');
    loadAll(null);
  };

  const saveNote = async (paperId: number) => {
    await api.patch(`/api/library/save/${paperId}`, { private_notes: noteDraft });
    setEditingNoteId(null);
    showToast('Private note saved');
    loadAll(selectedColId);
  };

  const moveCollection = async (paperId: number, colId: string) => {
    await api.patch(`/api/library/save/${paperId}`, { collection_id: colId ? Number(colId) : 0 });
    showToast('Updated collection assignment');
    loadAll(selectedColId);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Personal Collections</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Organize saved papers by topic, course, or project with private annotations.
          </p>
        </div>
        <Link to="/library" className="btn-secondary text-xs">
          Back to Library
        </Link>
      </div>

      <div className="grid lg:grid-cols-12 gap-6 items-start">
        <aside className="lg:col-span-3 space-y-4">
          <div className="surface-card p-3 space-y-1">
            <button
              onClick={() => setSelectedColId(null)}
              className={`w-full text-left rounded-md px-3 py-2 text-xs font-medium transition-colors ${
                selectedColId === null ? 'bg-[#142B4A] text-white' : 'text-[#263247] hover:bg-[#FAF8F2]'
              }`}
            >
              All Saved Publications
            </button>

            {collections.map((c) => (
              <div
                key={c.id}
                className={`rounded-md px-3 py-2 text-xs ${
                  selectedColId === c.id
                    ? 'bg-[#E9EFE8] text-[#2E5438] font-semibold'
                    : 'text-[#263247] hover:bg-[#FAF8F2]'
                }`}
              >
                {renamingId === c.id ? (
                  <div className="flex gap-1.5">
                    <input
                      value={renameDraft}
                      onChange={(e) => setRenameDraft(e.target.value)}
                      className="input-field text-xs py-1 px-2"
                    />
                    <button onClick={() => saveRename(c.id)} className="btn-accent text-[11px] px-2 py-1">
                      Save
                    </button>
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-1.5">
                    <button onClick={() => setSelectedColId(c.id)} className="flex-1 text-left truncate">
                      {c.name} <span className="text-[#8A92A0]">({c.item_count})</span>
                    </button>
                    <button
                      onClick={() => {
                        setRenamingId(c.id);
                        setRenameDraft(c.name);
                      }}
                      className="text-[#8A92A0] hover:text-[#142B4A]"
                      title="Rename"
                    >
                      <Edit2 className="h-3 w-3" />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(c)}
                      className="text-[#8A92A0] hover:text-rose-600"
                      title="Delete"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>

          <form onSubmit={createCol} className="surface-card p-4 space-y-2.5">
            <div className="text-xs font-semibold text-[#142B4A] flex items-center gap-1.5">
              <FolderPlus className="h-4 w-4 text-[#8E6914]" /> New Collection
            </div>
            <input
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Collection name"
              className="input-field text-xs py-1.5"
            />
            <input
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              placeholder="Optional description"
              className="input-field text-xs py-1.5"
            />
            <button type="submit" className="btn-primary w-full text-xs py-1.5">
              Create Collection
            </button>
          </form>
        </aside>

        <div className="lg:col-span-9 space-y-3">
          {loading ? (
            <CardSkeleton rows={3} />
          ) : items.length === 0 ? (
            <EmptyState
              icon={FolderOpen}
              title="No papers in this collection"
              description="Save publications from Discover Research and assign them to this folder."
              action={<Link to="/discover" className="btn-primary text-xs">Explore Papers</Link>}
            />
          ) : (
            items.map((p) => (
              <div key={p.id} className="surface-card p-5 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div>
                    <Link to={`/papers/${p.id}`} className="text-[15px] font-semibold text-[#142B4A] hover:text-[#8E6914]">
                      {p.title}
                    </Link>
                    <div className="text-xs text-[#697386] mt-0.5">
                      {(p.authors || []).slice(0, 3).join(', ')}
                      {p.publication_year ? ` · ${p.publication_year}` : ''}
                      {p.venue ? ` · ${p.venue}` : ''}
                    </div>
                  </div>
                  <select
                    value={p.my_collection_id || ''}
                    onChange={(e) => moveCollection(p.id, e.target.value)}
                    className="input-field w-auto text-xs bg-white py-1.5 shrink-0"
                  >
                    <option value="">Uncategorized</option>
                    {collections.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>

                {editingNoteId === p.id ? (
                  <div className="space-y-2">
                    <textarea
                      rows={2}
                      value={noteDraft}
                      onChange={(e) => setNoteDraft(e.target.value)}
                      className="input-field text-xs"
                    />
                    <div className="flex gap-2">
                      <button onClick={() => saveNote(p.id)} className="btn-accent text-xs py-1.5 px-3">
                        <Save className="h-3.5 w-3.5" /> Save Note
                      </button>
                      <button onClick={() => setEditingNoteId(null)} className="btn-secondary text-xs py-1.5 px-3">
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-3 rounded-md bg-[#FAF8F2] border border-[#E6E2D8] px-3.5 py-2.5 text-xs">
                    <div className="text-[#3B485C]">
                      <span className="font-medium text-[#697386]">Private note: </span>
                      {p.my_private_notes || <span className="italic text-[#8A92A0]">No note added yet</span>}
                    </div>
                    <button
                      onClick={() => {
                        setEditingNoteId(p.id);
                        setNoteDraft(p.my_private_notes || '');
                      }}
                      className="text-[#8E6914] font-medium hover:underline shrink-0"
                    >
                      Edit
                    </button>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Delete collection?"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? Your saved papers will remain in your library as uncategorized items.`}
        confirmLabel="Delete Collection"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
