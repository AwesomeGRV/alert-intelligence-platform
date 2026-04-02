import React from 'react';
import { useQuery } from 'react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchAlertTrends } from '../services/api';

function AlertSeverityChart() {
  const { data: trendsData, isLoading } = useQuery(
    'alert-trends-severity',
    () => fetchAlertTrends(24),
    { refetchInterval: 60000 }
  );

  if (isLoading) {
    return (
      <div className="h-64 skeleton rounded"></div>
    );
  }

  // Mock data for demonstration
  const mockData = [
    { severity: 'Critical', count: 12, color: '#ef4444' },
    { severity: 'High', count: 28, color: '#f59e0b' },
    { severity: 'Medium', count: 45, color: '#3b82f6' },
    { severity: 'Low', count: 67, color: '#10b981' },
    { severity: 'Info', count: 23, color: '#6b7280' }
  ];

  const data = trendsData?.severityBreakdown || mockData;

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis 
            dataKey="severity" 
            tick={{ fontSize: 12 }}
          />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip 
            content={({ active, payload }) => {
              if (active && payload && payload[0]) {
                const data = payload[0].payload;
                return (
                  <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
                    <p className="font-medium">{data.severity}</p>
                    <p className="text-sm text-gray-600">{data.count} alerts</p>
                  </div>
                );
              }
              return null;
            }}
          />
          <Bar 
            dataKey="count" 
            fill="#3b82f6"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export default AlertSeverityChart;
