import React, { createContext, useCallback, useContext, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

type ToastVariant = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  message: string;
  variant: ToastVariant;
}

interface ToastContextValue {
  showToast: (message: string, variant?: ToastVariant) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const showToast = useCallback((message: string, variant: ToastVariant = 'success') => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    setToasts((prev) => [...prev, { id, message, variant }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3600);
  }, []);

  const dismiss = (id: number) => setToasts((prev) => prev.filter((t) => t.id !== id));

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none px-4 sm:px-0">
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className={`pointer-events-auto flex items-start gap-2.5 rounded-lg border px-4 py-3 text-sm shadow-dropdown bg-white ${
              t.variant === 'error'
                ? 'border-rose-200 text-rose-900'
                : t.variant === 'info'
                ? 'border-[#DCD7CA] text-[#263247]'
                : 'border-[#CFE0CC] text-[#142B4A]'
            }`}
          >
            {t.variant === 'error' ? (
              <AlertCircle className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            ) : t.variant === 'info' ? (
              <Info className="h-4 w-4 text-[#142B4A] shrink-0 mt-0.5" />
            ) : (
              <CheckCircle2 className="h-4 w-4 text-[#8E6914] shrink-0 mt-0.5" />
            )}
            <span className="flex-1 text-xs font-medium leading-relaxed">{t.message}</span>
            <button onClick={() => dismiss(t.id)} className="text-[#8A92A0] hover:text-[#263247]">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}
