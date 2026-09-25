import React, { useState } from 'react';
import { useAuthStore } from '../store/authStore';
import { Shield, Bell, Settings, Save } from 'lucide-react';
import { cn } from '../components/common/MetricCard';

export const Profile: React.FC = () => {
  const { user } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'PREFERENCES' | 'SECURITY' | 'NOTIFICATIONS'>('PREFERENCES');

  const [toggles, setToggles] = useState({
    emailAlerts: true,
    pushNotifications: false,
    twoFactor: true,
  });

  const toggle = (key: keyof typeof toggles) => setToggles(p => ({ ...p, [key]: !p[key] }));

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold font-heading text-gray-900">Profile & Settings</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Sidebar Tabs */}
        <div className="card bg-white rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 p-2 space-y-1 h-fit">
          <button
            onClick={() => setActiveTab('PREFERENCES')}
            className={cn("w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors", activeTab === 'PREFERENCES' ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-50")}
          >
            <Settings size={18} /> Preferences
          </button>
          <button
            onClick={() => setActiveTab('SECURITY')}
            className={cn("w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors", activeTab === 'SECURITY' ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-50")}
          >
            <Shield size={18} /> Security
          </button>
          <button
            onClick={() => setActiveTab('NOTIFICATIONS')}
            className={cn("w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors", activeTab === 'NOTIFICATIONS' ? "bg-primary/10 text-primary" : "text-gray-600 hover:bg-gray-50")}
          >
            <Bell size={18} /> Notifications
          </button>
        </div>

        {/* Content Area */}
        <div className="md:col-span-3 space-y-6">
          <div className="card bg-white rounded-xl shadow-[0_2px_8px_rgba(0,0,0,0.06)] border border-gray-100 overflow-hidden">
            <div className="px-6 py-6 border-b border-gray-100 flex items-center gap-5">
              {/* Circular Badge Avatar with initials and purple/green gradient */}
              <div className="w-20 h-20 rounded-full flex items-center justify-center text-3xl font-bold text-[#0F5B3D] bg-gradient-to-br from-purple-200 to-green-200 shadow-sm border border-white/50">
                {(user?.name || 'U').slice(0, 2).toUpperCase()}
              </div>
              <div>
                <h2 className="text-xl font-bold text-gray-900">{user?.name || 'User Profile'}</h2>
                <p className="text-sm text-gray-500 capitalize font-medium mt-0.5">{(user?.role || 'Guest').toLowerCase().replace('_', ' ')}</p>
              </div>
            </div>

            <div className="p-6 space-y-6 min-h-[280px]">
              {activeTab === 'PREFERENCES' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Language</label>
                    <select className="w-full max-w-sm px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0F5B3D]/30 focus:border-[#0F5B3D] transition-shadow">
                      <option>English (US)</option>
                      <option>Hindi</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-700 mb-1.5">Timezone</label>
                    <select className="w-full max-w-sm px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0F5B3D]/30 focus:border-[#0F5B3D] transition-shadow">
                      <option>Asia/Kolkata (IST)</option>
                      <option>UTC</option>
                    </select>
                  </div>
                </div>
              )}

              {activeTab === 'SECURITY' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between py-2 border-b border-gray-100 pb-4">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900">Two-Factor Authentication</h4>
                      <p className="text-xs text-gray-500 mt-1">Add an extra layer of security to your account.</p>
                    </div>
                    {/* Toggle switch */}
                    <button 
                      onClick={() => toggle('twoFactor')}
                      className={cn("w-12 h-6 rounded-full transition-colors relative focus:outline-none", toggles.twoFactor ? "bg-[#0F5B3D]" : "bg-gray-200")}
                    >
                      <span className={cn("absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform shadow-sm", toggles.twoFactor ? "translate-x-6" : "translate-x-0")} />
                    </button>
                  </div>
                  <div className="pt-2">
                    <label className="block text-sm font-semibold text-gray-700 mb-2">Change Password</label>
                    <input type="password" placeholder="Current password" className="w-full max-w-sm px-4 py-2.5 mb-3 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0F5B3D]/30 focus:border-[#0F5B3D] transition-shadow" />
                    <input type="password" placeholder="New password" className="w-full max-w-sm px-4 py-2.5 rounded-lg border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-[#0F5B3D]/30 focus:border-[#0F5B3D] transition-shadow" />
                  </div>
                </div>
              )}

              {activeTab === 'NOTIFICATIONS' && (
                <div className="space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <div className="flex items-center justify-between py-4 border-b border-gray-100">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900">Email Alerts</h4>
                      <p className="text-xs text-gray-500 mt-1">Receive daily summaries and critical alerts via email.</p>
                    </div>
                    <button 
                      onClick={() => toggle('emailAlerts')}
                      className={cn("w-12 h-6 rounded-full transition-colors relative focus:outline-none", toggles.emailAlerts ? "bg-[#0F5B3D]" : "bg-gray-200")}
                    >
                      <span className={cn("absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform shadow-sm", toggles.emailAlerts ? "translate-x-6" : "translate-x-0")} />
                    </button>
                  </div>
                  <div className="flex items-center justify-between py-4 border-b border-gray-100">
                    <div>
                      <h4 className="text-sm font-semibold text-gray-900">Push Notifications</h4>
                      <p className="text-xs text-gray-500 mt-1">Receive in-app notifications for realtime events.</p>
                    </div>
                    <button 
                      onClick={() => toggle('pushNotifications')}
                      className={cn("w-12 h-6 rounded-full transition-colors relative focus:outline-none", toggles.pushNotifications ? "bg-[#0F5B3D]" : "bg-gray-200")}
                    >
                      <span className={cn("absolute top-1 left-1 bg-white w-4 h-4 rounded-full transition-transform shadow-sm", toggles.pushNotifications ? "translate-x-6" : "translate-x-0")} />
                    </button>
                  </div>
                </div>
              )}
            </div>

            <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end rounded-b-xl">
              <button className="flex items-center gap-2 px-5 py-2.5 bg-[#0F5B3D] hover:bg-[#1B7A4D] text-white text-sm font-semibold rounded-lg shadow-sm hover:shadow-md transition-all">
                <Save size={16} /> Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
