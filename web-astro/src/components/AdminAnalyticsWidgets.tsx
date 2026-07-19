import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { PieChart, Pie, Cell, Tooltip as PieTooltip, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip as BarTooltip } from 'recharts';
import { getAverageTrust, getSessionsPerOrg, getTacticsFrequency, type TacticFrequency, type SessionsPerOrg, type AverageTrust } from '../lib/api';

export default function AdminAnalyticsWidgets() {
  const { getToken, isLoaded } = useAuth();
  
  const [avgTrust, setAvgTrust] = useState<number | null>(null);
  const [orgData, setOrgData] = useState<SessionsPerOrg[]>([]);
  const [tacticData, setTacticData] = useState<TacticFrequency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    async function loadData() {
      try {
        const token = (await getToken() || "mock_token");
        if (!token) return;
        
        const [trust, orgs, tactics] = await Promise.all([
          getAverageTrust(token),
          getSessionsPerOrg(token),
          getTacticsFrequency(token)
        ]);
        
        if (!cancelled) {
          setAvgTrust(trust.average_trust_score);
          
          // Map "None" and "unassigned" to something more readable
          const cleanOrgs = orgs.map(o => ({
            ...o,
            org_id: (o.org_id === 'None' || o.org_id === 'unassigned') ? 'Unassigned' : o.org_id
          }));
          setOrgData(cleanOrgs.sort((a, b) => b.session_count - a.session_count));
          
          setTacticData(tactics.sort((a, b) => b.frequency - a.frequency));
          setLoading(false);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) setLoading(false);
      }
    }
    loadData();
    return () => { cancelled = true; };
  }, [isLoaded, getToken]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center rounded-card border border-border bg-surface-800">
        <p className="text-sm text-text-muted animate-pulse">Loading analytics...</p>
      </div>
    );
  }

  const PIE_COLORS = ['#d3b773', '#e4e4e7', '#8b8d98', '#3f3f46', '#27272a'];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Widget 1: Average Trust */}
      <div className="rounded-card border border-border bg-surface-800 p-card flex flex-col justify-center items-center text-center h-[320px]">
        <h3 className="text-sm font-semibold text-text-secondary tracking-wide uppercase mb-6">Global Trust Score</h3>
        <div className="relative">
          <svg className="absolute inset-0 h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#27272a" strokeWidth="8" />
            <circle 
              cx="50" cy="50" r="45" fill="none" stroke="#d3b773" strokeWidth="8" 
              strokeDasharray={`${(avgTrust || 0) * 2.83} 283`}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="flex h-40 w-40 items-center justify-center rounded-full">
            <span className="text-5xl font-bold font-mono text-text-primary">
              {avgTrust !== null ? Math.round(avgTrust * 100) : '--'}
            </span>
          </div>
        </div>
        <p className="mt-6 text-xs text-text-muted">Average across all platform sessions</p>
      </div>

      {/* Widget 2: Sessions By Org */}
      <div className="rounded-card border border-border bg-surface-800 p-card h-[320px] flex flex-col">
        <h3 className="text-sm font-semibold text-text-primary tracking-wide mb-2">Sessions by Organization</h3>
        <div className="flex-1 w-full min-h-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={orgData}
                dataKey="session_count"
                nameKey="org_id"
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                stroke="none"
              >
                {orgData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <PieTooltip 
                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#e4e4e7' }}
                itemStyle={{ color: '#d3b773', fontWeight: 600 }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Widget 3: Tactic Frequency */}
      <div className="rounded-card border border-border bg-surface-800 p-card h-[320px] flex flex-col">
        <h3 className="text-sm font-semibold text-text-primary tracking-wide mb-4">Tactic Frequency</h3>
        <div className="flex-1 w-full min-h-0 text-xs">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={tacticData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis 
                dataKey="tactic_name" 
                type="category" 
                axisLine={false} 
                tickLine={false} 
                tick={{ fill: '#8b8d98', fontSize: 11 }} 
                width={100}
              />
              <BarTooltip 
                cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#e4e4e7' }}
                itemStyle={{ color: '#d3b773', fontWeight: 600 }}
                labelStyle={{ color: '#8b8d98', marginBottom: '4px' }}
              />
              <Bar dataKey="frequency" radius={[0, 4, 4, 0]} barSize={20}>
                {tacticData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={index === 0 ? '#d3b773' : '#3f3f46'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
