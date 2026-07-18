import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Toast {
  id: string;
  title: string;
  description?: string;
  variant?: 'default' | 'destructive' | 'success';
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastState>()(
  persist(
    (set) => ({
      toasts: [],
      addToast: (toast) =>
        set((state) => ({
          toasts: [...state.toasts, { ...toast, id: Math.random().toString(36).slice(2) }],
        })),
      removeToast: (id) =>
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        })),
    }),
    { name: 'toast-storage' }
  )
);

export function toast(options: Omit<Toast, 'id'>) {
  useToastStore.getState().addToast(options);
}