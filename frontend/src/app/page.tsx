'use client';

import Link from 'next/link';
import { Shield, ArrowRight, Menu, X } from 'lucide-react';
import { useState } from 'react';

export default function HomePage() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <nav className="border-b border-[#1a1a1a] bg-[#0a0a0a]/80 backdrop-blur-lg sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex justify-between items-center h-14">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-gray-300" />
              <span className="font-semibold text-gray-100">DepHealth</span>
            </div>
            <button className="sm:hidden p-2" onClick={() => setMenuOpen(!menuOpen)}>
              {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
            </button>
            <div className="hidden sm:flex items-center gap-6">
              <Link href="/dashboard" className="text-sm text-gray-400 hover:text-gray-200 transition-colors">Dashboard</Link>
              <a href="#features" className="text-sm text-gray-400 hover:text-gray-200 transition-colors">Features</a>
              <Link href="/login" className="px-4 py-1.5 bg-white text-black text-sm font-medium rounded-lg hover:bg-gray-200 transition-colors">
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </nav>

      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-12 pb-16">
        <div className="max-w-3xl">
          <p className="text-xs text-gray-500 uppercase tracking-widest mb-4">Predictive Dependency Health</p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight mb-6">
            Predict dependency risks<br />
            <span className="text-gray-400">before they become problems.</span>
          </h1>
          <p className="text-gray-500 text-base sm:text-lg max-w-xl mb-8 leading-relaxed">
            AI-powered analysis of maintainer health, CVE velocity, and ecosystem migration patterns to forecast risk 90 days out.
          </p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-white text-black font-medium rounded-xl hover:bg-gray-200 transition-all text-sm"
            >
              Launch Dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#features"
              className="inline-flex items-center justify-center px-6 py-3 border border-[#222222] text-gray-300 rounded-xl hover:bg-[#111111] transition-all text-sm"
            >
              View Features
            </a>
          </div>
        </div>

        <div className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            ['Ecosystems', '5+'],
            ['ML Models', '5'],
            ['Forecast Days', '90'],
            ['Risk Signals', '50+'],
          ].map(([label, value]) => (
            <div key={label} className="border border-[#1a1a1a] rounded-xl p-4">
              <p className="text-2xl font-bold text-white">{value}</p>
              <p className="text-xs text-gray-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="features" className="border-t border-[#1a1a1a] py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="max-w-xl mb-12">
            <h2 className="text-2xl font-bold text-white mb-3">How it works</h2>
            <p className="text-gray-500 text-sm">Three core models analyze your dependencies and predict future risk trajectories.</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            {[
              ['Maintainer Health', 'Analyzes commit frequency, PR response times, bus factor, and abandonment signals across 50+ data points.'],
              ['CVE Velocity', 'Forecasts vulnerability discovery rates using historical patterns and ML regression models trained on 10M+ CVEs.'],
              ['Upgrade Planning', 'Generates prioritized, time-boxed upgrade roadmaps with effort estimates and breaking change analysis.'],
            ].map(([title, desc]) => (
              <div key={title} className="border border-[#1a1a1a] rounded-xl p-6 hover:border-[#333] transition-colors">
                <h3 className="font-semibold text-white text-sm mb-2">{title}</h3>
                <p className="text-gray-500 text-xs leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-t border-[#1a1a1a] py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl font-bold text-white mb-3">Ready to get started?</h2>
          <p className="text-gray-500 text-sm mb-8 max-w-md mx-auto">Scan your first project and see predictive risk scores in minutes.</p>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 bg-white text-black font-medium rounded-xl hover:bg-gray-200 transition-all text-sm"
          >
            Open Dashboard <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-[#1a1a1a] py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center text-xs text-gray-600">
          DepHealth — Predictive Dependency Health Monitoring
        </div>
      </footer>
    </div>
  );
}