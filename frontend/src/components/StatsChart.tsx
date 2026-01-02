import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { MOCK_STATS, MOCK_STATS_DAILY, MOCK_STATS_YEARLY } from '../data/mock';
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
    if (apiData) {
      const grouped = new Map<string, any>();

      apiData.forEach(item => {
        const date = parseISO(item.period);
        let key = item.period;
        let label = '';

        // Format label based on timeRange
        if (timeRange === '30days') {
          label = format(date, 'd MMM', { locale: language === 'tr' ? tr : enUS }); // 12 Mar
        } else if (timeRange === '12months') {
          label = format(date, 'MMM yy', { locale: language === 'tr' ? tr : enUS }); // Mar 24
        } else {
          label = format(date, 'yyyy', { locale: language === 'tr' ? tr : enUS }); // 2024
        }

        if (!grouped.has(key)) {
          grouped.set(key, { name: label, originalDate: date });
        }
        const entry = grouped.get(key);
        const typeKey = item.type;

        entry[typeKey] = (entry[typeKey] || 0) + item.count;
      });

      return Array.from(grouped.values())
        .sort((a, b) => a.originalDate.getTime() - b.originalDate.getTime());
    }

    // Fallback to mock data
    switch (timeRange) {
      case '30days':
        return MOCK_STATS_DAILY;
      case 'all':
        return MOCK_STATS_YEARLY;
      case '12months':
      default:
        return MOCK_STATS;
    }
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