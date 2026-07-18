'use client';

import { useEffect, useState } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useToastStore } from '@/lib/toast';
import { cn } from '@/lib/utils';

export function Toaster() {
  const { toasts, removeToast } = useToastStore();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80 max-w-full">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onClose={removeToast} />
      ))}
    </div>
  );
}

function Toast({ toast, onClose }: { toast: { id: string; title: string; description?: string; variant?: 'default' | 'destructive' | 'success' }; onClose: (id: string) => void }) {
  useEffect(() => {
    const timer = setTimeout(() => onClose(toast.id), 5000);
    return () => clearTimeout(timer);
  }, [toast.id, onClose]);

  const variantStyles = {
    default: 'border-white/10 bg-gray-900/90 backdrop-blur-xl',
    destructive: 'border-red-500/20 bg-red-900/30 backdrop-blur-xl',
    success: 'border-green-500/20 bg-green-900/30 backdrop-blur-xl',
  };

  const iconMap = {
    default: <Info className="h-5 w-5 text-amber-400" />,
    destructive: <AlertCircle className="h-5 w-5 text-red-400" />,
    success: <CheckCircle className="h-5 w-5 text-green-400" />,
  };

  return (
    <div
      className={cn(
        'flex items-start gap-3 p-4 rounded-2xl border shadow-2xl animate-slide-up',
        variantStyles[toast.variant || 'default']
      )}
    >
      <div className="flex-shrink-0 mt-0.5">{iconMap[toast.variant || 'default']}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white">{toast.title}</p>
        {toast.description && (
          <p className="text-sm text-gray-300 mt-1">{toast.description}</p>
        )}
      </div>
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 text-gray-500 hover:text-white transition-colors"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}