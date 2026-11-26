import React from 'react';

export function formatTopicLabel(topic: string): string {
  if (!topic) return '';
  return topic
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function formatSourceLabel(source: string): string {
  const map: Record<string, string> = {
    openalex: 'OpenAlex',
    arxiv: 'arXiv',
    semantic_scholar: 'Semantic Scholar',
    rss: 'Research Feed',
    user_submission: 'Member Submission',
    synthetic: 'University Catalog',
  };
  return map[source?.toLowerCase()] || 'Scholarly Index';
}

export function formatRelativeDate(iso?: string | null): string {
  if (!iso) return '';
  const dt = new Date(iso);
  if (isNaN(dt.getTime())) return '';
  const diffSec = Math.floor((Date.now() - dt.getTime()) / 1000);
  if (diffSec < 60) return 'Just now';
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 86400 * 7) return `${Math.floor(diffSec / 86400)}d ago`;
  return dt.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function getInitials(name?: string): string {
  if (!name) return 'CR';
  const parts = name.replace(/^Dr\.\s+/i, '').trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

export function CardSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="surface-card p-5 animate-pulse space-y-3">
          <div className="h-4 bg-[#E9EDF3] rounded w-3/4" />
          <div className="h-3 bg-[#F1F4F8] rounded w-1/2" />
          <div className="h-3 bg-[#F1F4F8] rounded w-full" />
          <div className="flex gap-2 pt-1">
            <div className="h-5 w-20 bg-[#F1F4F8] rounded-full" />
            <div className="h-5 w-24 bg-[#F1F4F8] rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: any;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="surface-card p-10 text-center flex flex-col items-center justify-center space-y-2.5">
      <div className="h-11 w-11 rounded-full bg-[#F2F4F7] text-[#697386] flex items-center justify-center">
        <Icon className="h-5 w-5" />
      </div>
      <h3 className="text-sm font-semibold text-[#263247]">{title}</h3>
      <p className="text-xs text-[#697386] max-w-md leading-relaxed">{description}</p>
      {action && <div className="pt-2">{action}</div>}
    </div>
  );
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  danger = false,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#142B4A]/40 p-4">
      <div className="surface-card max-w-md w-full p-6 space-y-4 shadow-dropdown">
        <h3 className="text-base font-semibold text-[#142B4A]">{title}</h3>
        <p className="text-sm text-[#697386] leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2.5 pt-2">
          <button onClick={onCancel} className="btn-secondary">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={
              danger
                ? 'inline-flex items-center justify-center rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-700 transition-colors'
                : 'btn-primary'
            }
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
