'use client';

import { useState, useEffect, useCallback } from 'react';
import { Bell, Menu, Shield, Key, Globe, Users, ChevronRight, Save, Loader2 } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { settingsApi } from '@/lib/api';

type SectionKey = 'notifications' | 'api-keys' | 'integrations' | 'team' | 'security';

const sections: { key: SectionKey; icon: any; label: string; desc: string }[] = [
  { key: 'notifications', icon: Bell, label: 'Notifications', desc: 'Manage alert preferences' },
  { key: 'api-keys', icon: Key, label: 'API Keys', desc: 'Manage GitHub, NVD, OpenAI keys' },
  { key: 'integrations', icon: Globe, label: 'Integrations', desc: 'CI/CD, webhooks, SSO' },
  { key: 'team', icon: Users, label: 'Team', desc: 'Manage team members and roles' },
  { key: 'security', icon: Shield, label: 'Security', desc: '2FA, audit logs, policies' },
];

export default function SettingsPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [active, setActive] = useState<SectionKey | null>(null);
  const [data, setData] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    if (!active) return;
    setLoading(true);
    settingsApi.get(active)
      .then(r => setData(r.data.settings || {}))
      .catch(() => setData({}))
      .finally(() => setLoading(false));
  }, [active]);

  const handleSave = useCallback(async (section: string) => {
    setSaving(section);
    try {
      await settingsApi.updateSection(section, data);
    } catch { }
    setSaving(null);
  }, [data]);

  const update = (key: string, val: any) => {
    setData((prev: Record<string, any>) => ({ ...prev, [key]: val }));
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="lg:ml-56">
        <header className="sticky top-0 z-40 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-[#1a1a1a]">
          <div className="flex items-center justify-between h-12 px-4 sm:px-6">
            <div className="flex items-center gap-3">
              <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-1.5 rounded-lg hover:bg-[#1a1a1a] text-gray-400"><Menu className="h-4 w-4" /></button>
              <h1 className="font-semibold text-white text-sm">Settings</h1>
            </div>
          </div>
        </header>
        <main className="px-4 sm:px-6 pb-4 sm:pb-6 pt-2 space-y-2 max-w-2xl">
          <p className="text-[10px] text-gray-500">Manage your account and workspace settings</p>
          {active ? renderSection() : renderList()}
        </main>
      </div>
    </div>
  );

  function renderList() {
    return sections.map((s, i) => (
      <div key={i} onClick={() => setActive(s.key)} className="border border-[#1a1a1a] rounded-lg px-3 py-2.5 hover:border-[#333] transition-colors flex items-center justify-between cursor-pointer">
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-md bg-[#1a1a1a] flex items-center justify-center">
            <s.icon className="h-3.5 w-3.5 text-gray-400" />
          </div>
          <div>
            <h3 className="text-xs font-medium text-white">{s.label}</h3>
            <p className="text-[10px] text-gray-500">{s.desc}</p>
          </div>
        </div>
        <ChevronRight className="h-3.5 w-3.5 text-gray-600" />
      </div>
    ));
  }

  function renderSection() {
    return (
      <div>
        <button onClick={() => setActive(null)} className="text-[10px] text-gray-400 hover:text-white mb-3 transition-colors">← Back to settings</button>
        <div className="border border-[#1a1a1a] rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-medium text-white capitalize">{active!.replace('-', ' ')}</h2>
            <button
              onClick={() => handleSave(active!)}
              disabled={saving === active}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1a1a1a] hover:bg-[#222] text-xs text-gray-300 rounded-lg border border-[#2a2a2a] transition-colors disabled:opacity-50"
            >
              {saving === active ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
              Save
            </button>
          </div>

          {loading ? (
            <div className="text-center py-6 text-[10px] text-gray-500">Loading...</div>
          ) : active === 'notifications' ? (
            <NotificationsForm data={data} update={update} />
          ) : active === 'api-keys' ? (
            <ApiKeysForm data={data} update={update} />
          ) : active === 'integrations' ? (
            <IntegrationsForm data={data} update={update} />
          ) : active === 'team' ? (
            <TeamForm />
          ) : active === 'security' ? (
            <SecurityForm data={data} update={update} />
          ) : null}
        </div>
      </div>
    );
  }
}

function Toggle({ label, desc, checked, onChange }: { label: string; desc?: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-xs text-gray-300">{label}</p>
        {desc && <p className="text-[10px] text-gray-600">{desc}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`relative h-5 w-9 rounded-full transition-colors ${checked ? 'bg-blue-600' : 'bg-[#2a2a2a]'}`}
      >
        <span className={`absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white transition-transform ${checked ? 'translate-x-4' : ''}`} />
      </button>
    </div>
  );
}

function NotificationsForm({ data, update }: { data: any; update: (k: string, v: any) => void }) {
  const email = data.email_alerts || { enabled: false, email: '' };
  const slack = data.slack_webhook || { enabled: false, url: '' };
  const types = data.alert_types || {};
  return (
    <div className="space-y-3">
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Email Alerts</h3>
        <Toggle label="Enable email alerts" checked={email.enabled} onChange={v => update('email_alerts', { ...email, enabled: v })} />
        {email.enabled && (
          <input
            type="email" placeholder="you@example.com"
            value={email.email} onChange={e => update('email_alerts', { ...email, email: e.target.value })}
            className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500"
          />
        )}
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Slack Webhook</h3>
        <Toggle label="Enable Slack integration" checked={slack.enabled} onChange={v => update('slack_webhook', { ...slack, enabled: v })} />
        {slack.enabled && (
          <input
            type="url" placeholder="https://hooks.slack.com/services/..."
            value={slack.url} onChange={e => update('slack_webhook', { ...slack, url: e.target.value })}
            className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500"
          />
        )}
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Alert Types</h3>
        <Toggle label="New vulnerabilities" checked={!!types.new_vulns} onChange={v => update('alert_types', { ...types, new_vulns: v })} />
        <Toggle label="Scan complete" checked={!!types.scan_complete} onChange={v => update('alert_types', { ...types, scan_complete: v })} />
        <Toggle label="Fix available" checked={!!types.fix_available} onChange={v => update('alert_types', { ...types, fix_available: v })} />
        <Toggle label="Certificate expiry" checked={!!types.expired_certs} onChange={v => update('alert_types', { ...types, expired_certs: v })} />
      </div>
    </div>
  );
}

function ApiKeysForm({ data, update }: { data: any; update: (k: string, v: any) => void }) {
  const github = data.github || { token: '', username: '' };
  const nvd = data.nvd || { api_key: '' };
  const openai = data.openai || { api_key: '' };
  return (
    <div className="space-y-3">
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">GitHub</h3>
        <input type="text" placeholder="GitHub Token" value={github.token} onChange={e => update('github', { ...github, token: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500 font-mono" />
        <input type="text" placeholder="Username" value={github.username} onChange={e => update('github', { ...github, username: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500" />
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">NVD API Key</h3>
        <input type="password" placeholder="NVD API Key" value={nvd.api_key} onChange={e => update('nvd', { api_key: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500 font-mono" />
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">OpenAI API Key</h3>
        <input type="password" placeholder="sk-..." value={openai.api_key} onChange={e => update('openai', { api_key: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500 font-mono" />
      </div>
    </div>
  );
}

function IntegrationsForm({ data, update }: { data: any; update: (k: string, v: any) => void }) {
  const cicd = data.cicd || {};
  const webhooks = data.webhooks || {};
  const sso = data.sso || {};
  return (
    <div className="space-y-3">
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">CI/CD</h3>
        <input type="url" placeholder="Jenkins URL" value={cicd.jenkins_url || ''} onChange={e => update('cicd', { ...cicd, jenkins_url: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500" />
        <Toggle label="GitHub Actions" checked={!!cicd.github_actions} onChange={v => update('cicd', { ...cicd, github_actions: v })} />
        <Toggle label="GitLab CI" checked={!!cicd.gitlab_ci} onChange={v => update('cicd', { ...cicd, gitlab_ci: v })} />
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Webhooks</h3>
        <input type="url" placeholder="Webhook URL" value={webhooks.url || ''} onChange={e => update('webhooks', { ...webhooks, url: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500" />
        <input type="text" placeholder="Events (comma separated)" value={(webhooks.events || []).join(', ')} onChange={e => update('webhooks', { ...webhooks, events: e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean) })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500" />
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">SSO</h3>
        <Toggle label="Enable SSO" checked={!!sso.enabled} onChange={v => update('sso', { ...sso, enabled: v })} />
        {sso.enabled && (
          <>
            <select value={sso.provider || ''} onChange={e => update('sso', { ...sso, provider: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500">
              <option value="">Select provider</option>
              <option value="google">Google</option>
              <option value="github">GitHub</option>
              <option value="okta">Okta</option>
              <option value="azure">Azure AD</option>
            </select>
            <input type="text" placeholder="Client ID" value={sso.client_id || ''} onChange={e => update('sso', { ...sso, client_id: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500" />
            <input type="password" placeholder="Client Secret" value={sso.client_secret || ''} onChange={e => update('sso', { ...sso, client_secret: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500 font-mono" />
          </>
        )}
      </div>
    </div>
  );
}

function TeamForm() {
  return (
    <div className="p-3 bg-[#111] rounded-lg">
      <p className="text-[10px] text-gray-500">Team management will be available in a future update.</p>
    </div>
  );
}

function SecurityForm({ data, update }: { data: any; update: (k: string, v: any) => void }) {
  const tf = data.two_factor || {};
  const session = data.session || {};
  const audit = data.audit_log || {};
  return (
    <div className="space-y-3">
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Two-Factor Authentication</h3>
        <Toggle label="Enable 2FA" checked={!!tf.enabled} onChange={v => update('two_factor', { ...tf, enabled: v })} />
        {tf.enabled && (
          <select value={tf.method || 'app'} onChange={e => update('two_factor', { ...tf, method: e.target.value })} className="w-full bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-xs text-gray-300 outline-none focus:border-gray-500">
            <option value="app">Authenticator App</option>
            <option value="sms">SMS</option>
            <option value="email">Email</option>
          </select>
        )}
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Session</h3>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500 w-32">Timeout (minutes)</span>
          <input type="number" min={5} max={1440} value={session.timeout_minutes ?? 60} onChange={e => update('session', { ...session, timeout_minutes: parseInt(e.target.value) || 60 })} className="w-20 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-gray-300 outline-none focus:border-gray-500" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-gray-500 w-32">Max sessions</span>
          <input type="number" min={1} max={50} value={session.max_sessions ?? 5} onChange={e => update('session', { ...session, max_sessions: parseInt(e.target.value) || 5 })} className="w-20 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-gray-300 outline-none focus:border-gray-500" />
        </div>
      </div>
      <div className="p-3 bg-[#111] rounded-lg space-y-2">
        <h3 className="text-[11px] font-medium text-gray-300">Audit Log</h3>
        <Toggle label="Enable audit logging" checked={!!audit.enabled} onChange={v => update('audit_log', { ...audit, enabled: v })} />
        {audit.enabled && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-500 w-32">Retention (days)</span>
            <input type="number" min={7} max={365} value={audit.retention_days ?? 90} onChange={e => update('audit_log', { ...audit, retention_days: parseInt(e.target.value) || 90 })} className="w-20 bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2 py-1 text-xs text-gray-300 outline-none focus:border-gray-500" />
          </div>
        )}
      </div>
    </div>
  );
}
