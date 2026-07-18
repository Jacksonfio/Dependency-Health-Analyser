import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatRelativeTime(date: string | Date): string {
  const now = new Date();
  const then = new Date(date);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(date);
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical': return 'text-red-600 bg-red-100 dark:bg-red-900/30';
    case 'high': return 'text-orange-600 bg-orange-100 dark:bg-orange-900/30';
    case 'medium': return 'text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30';
    case 'low': return 'text-blue-600 bg-blue-100 dark:bg-blue-900/30';
    default: return 'text-gray-600 bg-gray-100 dark:bg-gray-900/30';
  }
}

export function getRiskColor(score: number): string {
  if (score >= 75) return 'text-red-600';
  if (score >= 50) return 'text-orange-600';
  if (score >= 25) return 'text-yellow-600';
  return 'text-green-600';
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return str.slice(0, length) + '...';
}