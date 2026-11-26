import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  ExternalLink,
  Loader2,
  Send,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';

const SUGGESTED_QUESTIONS = [
  'How does retrieval-augmented generation improve large language model accuracy?',
  'What approaches are used for federated learning and anomaly detection in data systems?',
  'What are recent advances in solid-state batteries and perovskite solar cells?',
  'How is machine learning applied to bioinformatics, protein folding, and genomics?',
  'What techniques optimize autonomous robotics and edge AI systems?',
];

interface QAExchange {
  question: string;
  response: any;
}

function FormattedAnswer({
  text,
  onSelectCitation,
}: {
  text: string;
  onSelectCitation: (idx: number) => void;
}) {
  return (
    <div className="text-sm text-[#263247] leading-[1.7] space-y-2">
      {String(text || '')
        .split('\n')
        .filter((line) => line.trim() !== '')
        .map((line, i) => {
          const isBullet = line.trim().startsWith('- ');
          const cleanLine = isBullet ? line.trim().slice(2) : line;
          const segments = cleanLine.split(/(\*\*[^*]+\*\*|\[\d+\])/g);
          return (
            <p key={i} className={isBullet ? 'pl-4 relative before:content-["•"] before:absolute before:left-0 before:text-[#8E6914]' : ''}>
              {segments.map((seg, j) => {
                if (seg.startsWith('**') && seg.endsWith('**')) {
                  return (
                    <strong key={j} className="font-semibold text-[#142B4A]">
                      {seg.slice(2, -2)}
                    </strong>
                  );
                }
                const citeMatch = seg.match(/^\[(\d+)\]$/);
                if (citeMatch) {
                  const num = Number(citeMatch[1]);
                  return (
                    <button
                      key={j}
                      type="button"
                      onClick={() => onSelectCitation(num)}
                      className="inline-flex items-center justify-center rounded bg-[#E9EFE8] text-[#2E5438] hover:bg-[#8E6914] hover:text-white px-1.5 py-0.2 mx-0.5 text-[11px] font-semibold transition-colors"
                      title={`View source [${num}]`}
                    >
                      [{num}]
                    </button>
                  );
                }
                return <React.Fragment key={j}>{seg}</React.Fragment>;
              })}
            </p>
          );
        })}
    </div>
  );
}

export default function AssistantPage() {
  const [question, setQuestion] = useState('');
  const [onlyLibrary, setOnlyLibrary] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<QAExchange[]>([]);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);

  const ask = async (qStr = question) => {
    const clean = qStr.trim();
    if (!clean || loading) return;
    setQuestion('');
    setLoading(true);
    setHighlightedCitation(null);
    try {
      const res = await api.post('/api/assistant/ask', {
        question: clean,
        top_k: 5,
        only_library: onlyLibrary,
      });
      setHistory((prev) => {
        const next = [...prev, { question: clean, response: res }];
        setActiveIndex(next.length - 1);
        return next;
      });
    } catch (err: any) {
      setHistory((prev) => {
        const next = [
          ...prev,
          {
            question: clean,
            response: {
              sufficient_evidence: false,
              answer: err.message || 'Unable to process this question right now.',
              citations: [],
              retrieved_passages: [],
            },
          },
        ];
        setActiveIndex(next.length - 1);
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const activeExchange = activeIndex >= 0 ? history[activeIndex] : null;
  const activeResponse = activeExchange?.response;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-semibold text-[#142B4A] tracking-tight">Research Assistant</h1>
          <p className="text-sm text-[#697386] mt-0.5">
            Ask research questions in plain language and review answers grounded directly in publications and supporting passages.
          </p>
        </div>
      </div>

      {/* Main Two-Pane Scholarly Layout */}
      <div className="grid lg:grid-cols-12 gap-6 items-start">
        {/* Left/Center Pane: Question Input & Grounded Conversation */}
        <div className="lg:col-span-7 space-y-4">
          <div className="surface-card p-5 space-y-3.5">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                ask();
              }}
              className="space-y-3"
            >
              <label htmlFor="assistant-question" className="block text-xs font-semibold text-[#142B4A]">
                Ask a research question
              </label>
              <div className="flex gap-2">
                <input
                  id="assistant-question"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g., What are the recent applications of machine learning in healthcare?"
                  className="input-field py-2.5"
                />
                <button type="submit" disabled={loading || !question.trim()} className="btn-primary px-5 shrink-0">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  <span>{loading ? 'Searching...' : 'Ask'}</span>
                </button>
              </div>
              <label className="inline-flex items-center gap-2 text-xs text-[#697386] cursor-pointer">
                <input
                  type="checkbox"
                  checked={onlyLibrary}
                  onChange={(e) => setOnlyLibrary(e.target.checked)}
                  className="rounded border-[#CFD7E3] text-[#8E6914] focus:ring-[#8E6914]"
                />
                Limit sources to publications saved in the university library
              </label>
            </form>

            {history.length === 0 && (
              <div className="pt-3 border-t border-[#F0ECE2] space-y-2">
                <div className="text-xs font-medium text-[#697386]">Suggested questions:</div>
                <div className="flex flex-col gap-1.5">
                  {SUGGESTED_QUESTIONS.map((sq) => (
                    <button
                      key={sq}
                      type="button"
                      onClick={() => ask(sq)}
                      className="text-left rounded-md border border-[#E6E2D8] bg-[#FAF8F2] hover:border-[#8E6914] hover:bg-white px-3.5 py-2 text-xs text-[#263247] transition-colors"
                    >
                      {sq}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Conversation Exchanges */}
          {history.map((item, idx) => {
            const resp = item.response;
            const isSelected = idx === activeIndex;
            const citeCount = (resp.citations || []).length;
            return (
              <div
                key={idx}
                onClick={() => setActiveIndex(idx)}
                className={`surface-card p-6 space-y-4 cursor-pointer transition-colors ${
                  isSelected ? 'border-[#8E6914]' : 'hover:border-[#CFD7E3]'
                }`}
              >
                <div className="flex items-start justify-between gap-3 border-b border-[#F0ECE2] pb-3">
                  <h2 className="text-sm font-semibold text-[#142B4A]">{item.question}</h2>
                  {citeCount > 0 && (
                    <span className="subtle-badge shrink-0">
                      {citeCount} {citeCount === 1 ? 'source' : 'sources'}
                    </span>
                  )}
                </div>

                {!resp.sufficient_evidence ? (
                  <div className="flex items-start gap-2.5 rounded-md bg-amber-50 border border-amber-200 p-3.5 text-xs text-amber-900 leading-relaxed">
                    <AlertCircle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <div className="font-semibold mb-0.5">Insufficient supporting publications</div>
                      <p>{resp.answer}</p>
                    </div>
                  </div>
                ) : (
                  <FormattedAnswer
                    text={resp.answer}
                    onSelectCitation={(n) => {
                      setActiveIndex(idx);
                      setHighlightedCitation(n);
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Right Pane: Supporting Publications & Evidence Passages */}
        <aside className="lg:col-span-5">
          <div className="surface-card p-5 sticky top-20 space-y-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-[#E6E2D8] pb-3">
              <div>
                <h2 className="text-sm font-semibold text-[#142B4A] flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-[#8E6914]" /> Supporting Publications & Evidence
                </h2>
                {activeResponse && (activeResponse.retrieved_passages || []).length > 0 && (
                  <p className="text-xs text-[#697386] mt-0.5">
                    These {activeResponse.retrieved_passages.length} publications were used to prepare your answer.
                  </p>
                )}
              </div>
            </div>

            {!activeResponse ? (
              <div className="py-10 text-center space-y-2">
                <Sparkles className="h-6 w-6 text-[#CBD5E1] mx-auto" />
                <p className="text-xs text-[#697386] max-w-xs mx-auto leading-relaxed">
                  Ask a research question to inspect the exact publications, citations, and quoted passages behind every answer.
                </p>
              </div>
            ) : (activeResponse.retrieved_passages || []).length === 0 ? (
              <p className="text-xs text-[#697386] py-6 text-center">
                No sufficiently relevant passages were found in the current research catalog for this query.
              </p>
            ) : (
              <div className="space-y-3">
                {activeResponse.retrieved_passages.map((p: any) => {
                  const isHi = highlightedCitation === p.citation_index;
                  return (
                    <div
                      key={p.paper_id}
                      className={`rounded-md border p-4 space-y-2 transition-colors ${
                        isHi
                          ? 'border-[#8E6914] bg-[#E9EFE8]/60'
                          : 'border-[#E6E2D8] bg-[#FAF8F2]/60'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-[#142B4A] text-white text-[11px] font-semibold shrink-0 mt-0.5">
                          {p.citation_index}
                        </span>
                        <div className="min-w-0">
                          <Link
                            to={`/papers/${p.paper_id}`}
                            className="text-xs font-semibold text-[#142B4A] hover:text-[#8E6914] leading-snug block"
                          >
                            {p.title}
                          </Link>
                          <div className="text-[11px] text-[#697386] mt-0.5">
                            {(p.authors || []).slice(0, 2).join(', ')}
                            {p.publication_year ? ` · ${p.publication_year}` : ''}
                            {p.venue ? ` · ${p.venue}` : ''}
                          </div>
                        </div>
                      </div>

                      <blockquote className="text-xs text-[#3B485C] leading-relaxed border-l-2 border-[#8E6914] pl-3 italic">
                        "{p.passage}"
                      </blockquote>

                      <div className="flex items-center gap-3 pt-1 text-[11px]">
                        <Link to={`/papers/${p.paper_id}`} className="font-medium text-[#8E6914] hover:underline">
                          Inspect Publication
                        </Link>
                        {p.url && (
                          <a
                            href={p.url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-[#697386] hover:text-[#142B4A]"
                          >
                            Original Source <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
