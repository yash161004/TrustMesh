import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/astro/react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { getTacticsFrequency, type TacticFrequency } from '../lib/api';

export default function AdminTacticsChart() {
  const { getToken, isLoaded } = useAuth();
  const [data, setData] = useState<TacticFrequency[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoaded) return;
    let cancelled = false;
    async function fetchFreq() {
      try {
        const token = (await getToken() || "mock_token");
        if (token) {
          const res = await getTacticsFrequency(token);
          if (!cancelled) setData(res.sort((a, b) => b.frequency - a.frequency));
        }
      } catch (err) {
        console.error(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchFreq();
    return () => { cancelled = true; };
  }, [isLoaded, getToken]);

  if (loading) {
    return (
      <div className="rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex items-center justify-center">
        <p className="text-sm text-text-muted animate-pulse">Loading tactics data...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex flex-col items-center justify-center">
        <h2 className="mb-2 text-sm font-semibold text-text-primary tracking-wide">Tactic Frequency</h2>
        <p className="text-sm text-text-muted">No manipulation tactics detected yet.</p>
      </div>
    );
  }

  return (
    <div className="rounded-card border border-border bg-surface-800 px-card py-card h-[320px] flex flex-col">
      <h2 className="mb-4 text-sm font-semibold text-text-primary tracking-wide">Tactic Frequency</h2>
      <div className="flex-1 min-h-0 w-full text-xs">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 30, left: 10, bottom: 0 }}>
            <XAxis type="number" hide />
            <YAxis 
              dataKey="tactic_name" 
              type="category" 
              axisLine={false} 
              tickLine={false} 
              tick={{ fill: '#8b8d98', fontSize: 11 }} 
              width={160}
            />
            <Tooltip 
              cursor={{ fill: 'rgba(255,255,255,0.02)' }}
              contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '8px', fontSize: '12px', color: '#e4e4e7' }}
              itemStyle={{ color: '#d3b773', fontWeight: 600 }}
              labelStyle={{ color: '#8b8d98', marginBottom: '4px' }}
            />
            <Bar dataKey="frequency" radius={[0, 4, 4, 0]} barSize={24}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={index === 0 ? '#d3b773' : '#3f3f46'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
