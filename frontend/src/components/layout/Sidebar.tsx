'use client';

import { LayoutDashboard, Package, AlertTriangle, TrendingUp, Settings, Scale, Clock, GitBranch, Wrench, LogOut, ChevronLeft, Shield, Search } from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const nav = [
  { name: 'Analyze', href: '/dashboard/analyze', icon: Search, accent: 'text-amber-400' },
  { name: 'Overview', href: '/dashboard', icon: LayoutDashboard, accent: 'text-emerald-400' },
  { name: 'Projects', href: '/dashboard/projects', icon: Package, accent: 'text-violet-400' },
  { name: 'Vulnerabilities', href: '/dashboard/vulnerabilities', icon: AlertTriangle, accent: 'text-rose-400' },
  { name: 'Risk Prediction', href: '/dashboard/risk-timeline', icon: TrendingUp, accent: 'text-orange-400' },
  { name: 'Licenses', href: '/dashboard/licenses', icon: Scale, accent: 'text-amber-400' },
  { name: 'Impact Sim', href: '/dashboard/impact-simulator', icon: GitBranch, accent: 'text-teal-400' },
  { name: 'Remediation', href: '/dashboard/remediation', icon: Wrench, accent: 'text-rose-400' },
  { name: 'Vuln Aging', href: '/dashboard/vulnerability-aging', icon: Clock, accent: 'text-orange-400' },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings, accent: 'text-stone-400' },
];

export function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const path = usePathname();

  return (
    <>
      <div className={`fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden transition-opacity ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} onClick={onClose} />
      <aside className={`fixed lg:static inset-y-0 left-0 z-50 w-56 bg-gradient-to-b from-[#0c0a09] via-[#0c0a09] to-[#0a0807] border-r border-stone-800/80 transform transition-transform duration-300 flex flex-col ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        {/* Brand header with amber accent */}
        <div className="relative flex items-center justify-between h-14 px-4 border-b border-stone-800/60 bg-gradient-to-r from-amber-500/5 to-rose-500/5">
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center shadow-lg shadow-amber-500/20">
              <Shield className="h-3.5 w-3.5 text-white" />
            </div>
            <div>
              <span className="font-semibold text-sm text-white group-hover:text-amber-300 transition-colors">DepHealth</span>
              <p className="text-[8px] text-stone-500 tracking-wider uppercase">Risk Monitor</p>
            </div>
          </Link>
          <button onClick={onClose} className="lg:hidden p-1 rounded hover:bg-stone-800 text-stone-500">
            <ChevronLeft className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5">
          {nav.map((item) => {
            const active = path === item.href || path.startsWith(item.href + '/');
            return (
              <Link key={item.name} href={item.href} onClick={onClose}
                className={cn(
                  'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-all group',
                  active
                    ? 'bg-gradient-to-r from-amber-500/10 to-transparent text-white border-l-2 border-l-amber-500'
                    : 'text-stone-500 hover:text-stone-200 hover:bg-stone-800/40 border-l-2 border-l-transparent'
                )}
              >
                <item.icon className={cn('h-4 w-4', active ? item.accent : 'text-stone-600 group-hover:text-stone-400')} />
                {item.name}
                {active && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_6px_rgba(245,158,11,0.5)]" />}
              </Link>
            );
          })}
        </nav>

        <div className="p-3 border-t border-stone-800/60">
          <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg bg-stone-800/20">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-amber-500 to-rose-600 flex items-center justify-center shadow-md">
              <span className="text-xs font-bold text-white">JD</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-stone-200 truncate font-medium">John Doe</p>
              <p className="text-[9px] text-stone-600 truncate">john@example.com</p>
            </div>
          </div>
          <button className="mt-2 flex items-center gap-2.5 px-3 py-2 text-xs text-stone-600 hover:text-stone-400 hover:bg-stone-800/30 rounded-lg w-full transition-colors">
            <LogOut className="h-3.5 w-3.5" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
