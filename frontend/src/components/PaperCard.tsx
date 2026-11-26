import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Bookmark, BookmarkCheck, ExternalLink, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { formatSourceLabel, formatTopicLabel } from './UIPrimitives';

export interface PaperItem {
  id: number;
  title: string;
  abstract: string;
  authors: string[];
  publication_year?: number;
  venue?: string;
  doi?: string;
  arxiv_id?: string;
  url?: string;
  topics: string[];
  department_hint?: string;
  primary_source: string;
  sources?: { source: string; external_id?: string; url?: string }[];
  citation_count: number;
  pagerank_score?: number;
  save_count: number;
  in_university_library: boolean;
  is_synthetic?: boolean;
  is_saved_by_me?: boolean;
  relevance_score?: number;
  reasons?: string[];
}

export default function PaperCard({
  paper,
  compact = false,
  highlightNote,
  onSaveChanged,
}: {
  paper: PaperItem;
  compact?: boolean;
  highlightNote?: string;
  onSaveChanged?: (paperId: number, saved: boolean) => void;
}) {
  const { user } = useAuth();
  const { showToast } = useToast();
  const [saved, setSaved] = useState(!!paper.is_saved_by_me);
  const [saveCount, setSaveCount] = useState(paper.save_count || 0);
  const [busy, setBusy] = useState(false);

  const toggleSave = async () => {
    if (!user || busy) return;
    setBusy(true);
    try {
      if (saved) {
        const res = await api.del(`/api/library/save/${paper.id}`);
        setSaved(false);
        setSaveCount(res.save_count ?? Math.max(0, saveCount - 1));
        onSaveChanged?.(paper.id, false);
        showToast('Removed from your library', 'info');
      } else {
        const res = await api.post('/api/library/save', { paper_id: paper.id });
        setSaved(true);
        setSaveCount(res.paper?.save_count ?? saveCount + 1);
        onSaveChanged?.(paper.id, true);
        showToast('Saved to your research library');
      }
    } catch (err: any) {
      showToast(err.message || 'Could not update library', 'error');
    } finally {
      setBusy(false);
    }
  };

  const uniqueSources = Array.from(
    new Set((paper.sources || []).map((s) => formatSourceLabel(s.source)).filter(Boolean))
  );
  if (uniqueSources.length === 0 && paper.primary_source) {
    uniqueSources.push(formatSourceLabel(paper.primary_source));
  }

  const authorsDisplay =
    (paper.authors || []).length > 0
      ? (paper.authors || []).slice(0, 3).join(', ') + ((paper.authors || []).length > 3 ? ' et al.' : '')
      : 'University Archive';

  const explanation =
    highlightNote || (paper.reasons && paper.reasons.length > 0 ? paper.reasons[0] : null);

  return (
    <article className="surface-card-interactive p-5 flex flex-col gap-2.5">
      {explanation && (
        <div className="text-[11px] font-medium text-[#8E6914] flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[#D6AA35]" />
          {explanation}
        </div>
      )}

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <Link
            to={`/papers/${paper.id}`}
            className="text-[15px] font-semibold text-[#142B4A] hover:text-[#8E6914] leading-snug block transition-colors"
          >
            {paper.title}
          </Link>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-[#697386]">
            <span className="truncate max-w-md">{authorsDisplay}</span>
            {paper.publication_year && <span>· {paper.publication_year}</span>}
            {paper.venue && (
              <span className="text-[#3B485C] font-medium truncate max-w-xs">· {paper.venue}</span>
            )}
          </div>
        </div>

        {user && (
          <button
            onClick={toggleSave}
            disabled={busy}
            aria-label={saved ? 'Remove from library' : 'Save to library'}
            className={`shrink-0 inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium border transition-colors ${
              saved
                ? 'bg-[#FBF5E4] border-[#E7D49A] text-[#8E6914]'
                : 'bg-white border-[#DCD7CA] text-[#263247] hover:bg-[#FAF8F2]'
            }`}
          >
            {saved ? (
              <BookmarkCheck className="h-3.5 w-3.5 text-[#A67E1E]" />
            ) : (
              <Bookmark className="h-3.5 w-3.5 text-[#697386]" />
            )}
            <span>{saved ? 'Saved' : 'Save'}</span>
          </button>
        )}
      </div>

      {!compact && paper.abstract && (
        <p className="text-[13px] text-[#4A5568] leading-relaxed line-clamp-3">
          {paper.abstract}
        </p>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2 pt-2.5 border-t border-[#F0ECE2]">
        <div className="flex flex-wrap items-center gap-1.5">
          {(paper.topics || []).slice(0, 3).map((t) => (
            <Link
              key={t}
              to={`/search?q=${encodeURIComponent(t.replace(/-/g, ' '))}`}
              className="topic-pill"
            >
              {formatTopicLabel(t)}
            </Link>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs text-[#697386]">
          {paper.citation_count > 0 && (
            <span>{paper.citation_count.toLocaleString()} citations</span>
          )}
          {saveCount > 0 && (
            <span className="sage-badge">
              <BookOpen className="h-3 w-3" />
              Saved by {saveCount}
            </span>
          )}
          <span className="text-[11px] text-[#8A92A0]">{uniqueSources.join(', ')}</span>
          {paper.url && (
            <a
              href={paper.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-[#142B4A] font-medium hover:text-[#8E6914]"
            >
              Open <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
