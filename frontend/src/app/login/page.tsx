'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Shield, Github, Mail, ArrowRight } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSignIn = () => {
    if (!email.trim() || !password.trim()) {
      setError('Please enter email and password');
      return;
    }
    setError('');
    router.push('/dashboard');
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex h-12 w-12 rounded-xl bg-[#1a1a1a] items-center justify-center mb-4">
            <Shield className="h-6 w-6 text-gray-400" />
          </div>
          <h1 className="text-xl font-bold text-white">Welcome to DepHealth</h1>
          <p className="text-xs text-gray-500 mt-1">Sign in to start predicting dependency risks</p>
        </div>
        <div className="border border-[#1a1a1a] rounded-xl p-6">
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" className="w-full px-3 py-2 bg-[#111111] border border-[#222222] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#444]" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">Password</label>
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSignIn()} placeholder="••••••••" className="w-full px-3 py-2 bg-[#111111] border border-[#222222] rounded-lg text-xs text-white placeholder-gray-600 focus:outline-none focus:border-[#444]" />
            </div>
            {error && <p className="text-[10px] text-red-400">{error}</p>}
            <button onClick={handleSignIn} className="w-full px-3 py-2 bg-white text-black text-xs font-medium rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-1.5">
              Sign In <ArrowRight className="h-3 w-3" />
            </button>
          </div>
          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-[#1a1a1a]" /></div>
            <div className="relative flex justify-center text-[10px]"><span className="bg-[#0a0a0a] px-2 text-gray-600">or continue with</span></div>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button onClick={() => router.push('/dashboard')} className="flex items-center justify-center gap-1.5 px-3 py-2 bg-[#1a1a1a] border border-[#333] rounded-lg text-[11px] text-gray-400 hover:bg-[#222] transition-colors">
              <Github className="h-3.5 w-3.5" /> GitHub
            </button>
            <button onClick={() => router.push('/dashboard')} className="flex items-center justify-center gap-1.5 px-3 py-2 bg-[#1a1a1a] border border-[#333] rounded-lg text-[11px] text-gray-400 hover:bg-[#222] transition-colors">
              <Mail className="h-3.5 w-3.5" /> Google
            </button>
          </div>
          <p className="mt-4 text-center text-[11px] text-gray-600">
            Don&apos;t have an account?{' '}
            <a href="#" onClick={e => { e.preventDefault(); router.push('/dashboard'); }} className="text-gray-400 hover:text-gray-200 font-medium transition-colors">Sign up</a>
          </p>
        </div>
        <p className="mt-4 text-center text-[10px] text-gray-700">
          <Link href="/" className="hover:text-gray-400 transition-colors">← Back to home</Link>
        </p>
      </div>
    </div>
  );
}