import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { StatsData } from '../lib/api';
import { format, parseISO } from 'date-fns';
import { enUS, tr } from 'date-fns/locale';
import { useLanguage } from '../store/language';

interface StatsChartProps {
  timeRange?: '30days' | '12months' | 'all';
  data?: StatsData[];
}



export function StatsChart({ timeRange = '30days', data: apiData }: StatsChartProps) {
  const { language } = useLanguage();

  // Transform API data if available
  const data = React.useMemo(() => {
    const grouped = new Map<string, any>();
    const today = new Date();

    // Pre-fill the map based on timeRange
    if (timeRange === '30days') {
      for (let i = 29; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        const key = d.toISOString().split('T')[0] + 'T00:00:00'; // Match API format roughly or just use ISO date part
        // Actually API returns full ISO string like 2024-03-25T00:00:00
        // Let's use a standard key format YYYY-MM-DD
        const standardKey = format(d, 'yyyy-MM-dd');
        grouped.set(standardKey, {
          name: format(d, 'd MMM', { locale: language === 'tr' ? tr : enUS }),
          originalDate: d
        });
      }
    } else if (timeRange === '12months') {
      for (let i = 11; i >= 0; i--) {
        const d = new Date(today);
        d.setMonth(d.getMonth() - i);
        d.setDate(1); // normalized to first of month
        const standardKey = format(d, 'yyyy-MM');
        grouped.set(standardKey, {
          name: format(d, 'MMM yy', { locale: language === 'tr' ? tr : enUS }),
          originalDate: d
        });
      }
    }
    // For 'all', we don't pre-fill because start date varies (1980), but we could fill gaps between min and max year if needed.
    // For now, let's just process 'all' as is, or fill gaps if user insists.
    // The user said "in charts, let it spare slots for empty dates too".
    // For year view, it's better to fill years between min and max.

    const processedApiData = (apiData || []).map(item => {
      const date = parseISO(item.period);
      let key = '';
      if (timeRange === '30days') key = format(date, 'yyyy-MM-dd');
      else if (timeRange === '12months') key = format(date, 'yyyy-MM');
      else key = format(date, 'yyyy');
      return { ...item, key, date };
    });

    // If 'all', find min/max and fill
    if (timeRange === 'all' && processedApiData.length > 0) {
      const minYear = Math.min(...processedApiData.map(d => d.date.getFullYear()));
      const maxYear = new Date().getFullYear();
      for (let y = minYear; y <= maxYear; y++) {
        const d = new Date(y, 0, 1);
        const key = String(y);
        if (!grouped.has(key)) {
          grouped.set(key, {
            name: String(y),
            originalDate: d
          });
        }
      }
    }

    // Merge API data
    processedApiData.forEach(item => {
      if (!grouped.has(item.key)) {
        // Should only happen if API returns date outside pre-filled range (e.g. timezone diffs)
        // or for 'all' mode if we missed some.
        // allow it.
        let label = '';
        if (timeRange === '30days') label = format(item.date, 'd MMM', { locale: language === 'tr' ? tr : enUS });
        else if (timeRange === '12months') label = format(item.date, 'MMM yy', { locale: language === 'tr' ? tr : enUS });
        else label = format(item.date, 'yyyy', { locale: language === 'tr' ? tr : enUS });

        grouped.set(item.key, { name: label, originalDate: item.date });
      }

      const entry = grouped.get(item.key);
      const typeKey = item.type;
      entry[typeKey] = (entry[typeKey] || 0) + item.count;
    });

    return Array.from(grouped.values())
    return Array.from(grouped.values())
      .sort((a, b) => a.originalDate.getTime() - b.originalDate.getTime());
  }, [timeRange, apiData, language]);

  return (
    <div className="w-full h-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 10,
            left: -20,
            bottom: 0,
          }}
          barSize={timeRange === '30days' ? 8 : 24}
        >
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e4e7" opacity={0.5} />
          <XAxis
            dataKey="name"
            tick={{ fill: '#71717a', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            dy={10}
            minTickGap={timeRange === '30days' ? 20 : 0}
          />
          <YAxis
            tick={{ fill: '#71717a', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: '#f4f4f5' }}
            contentStyle={{
              borderRadius: '8px',
              border: '1px solid #e4e4e7',
              boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
              backgroundColor: '#ffffff',
              fontSize: '12px',
              padding: '8px 12px'
            }}
            labelStyle={{ fontWeight: 600, marginBottom: '4px', color: '#18181b' }}
          />
          {/* Order matches legend: Kanun, KHK, CB Kararname, CB Yönetmelik, CB Karar, CB Genelge */}
          <Bar dataKey="kanun" name="Kanun" stackId="a" fill="#18181b" radius={[0, 0, 0, 0]} />
          <Bar dataKey="khk" name="KHK" stackId="a" fill="#dc2626" />
          <Bar dataKey="cb-kararname" name="CB Kararname" stackId="a" fill="#d97706" />
          <Bar dataKey="cb-yonetmelik" name="CB Yönetmelik" stackId="a" fill="#7c3aed" />
          <Bar dataKey="cb-karar" name="CB Karar" stackId="a" fill="#2563eb" />
          <Bar dataKey="cb-genelge" name="CB Genelge" stackId="a" fill="#059669" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}