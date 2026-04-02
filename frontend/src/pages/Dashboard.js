import React from 'react';
import { useQuery } from 'react-query';
import {
  BellIcon,
  ExclamationTriangleIcon,
  ServerIcon,
  ChartBarIcon,
  TrendingUpIcon,
  TrendingDownIcon
} from '@heroicons/react/outline';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

import { fetchDashboardOverview, fetchAlertTrends, fetchIncidentTrends } from '../services/api';
import StatCard from '../components/StatCard';
import AlertSeverityChart from '../components/AlertSeverityChart';
import RecentIncidents from '../components/RecentIncidents';
import ServiceHealth from '../components/ServiceHealth';

const COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6'];

function Dashboard() {
  const { data: overview, isLoading: overviewLoading } = useQuery(
    'dashboard-overview',
    fetchDashboardOverview,
    { refetchInterval: 30000 }
  );

  const { data: alertTrends, isLoading: trendsLoading } = useQuery(
    'alert-trends',
    () => fetchAlertTrends(24),
    { refetchInterval: 60000 }
  );

  const { data: incidentTrends, isLoading: incidentTrendsLoading } = useQuery(
    'incident-trends',
    () => fetchIncidentTrends(7),
    { refetchInterval: 120000 }
  );

  if (overviewLoading || trendsLoading || incidentTrendsLoading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="stat-card">
              <div className="stat-card-content">
                <div className="skeleton skeleton-title"></div>
                <div className="skeleton skeleton-line"></div>
              </div>
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card">
            <div className="card-body">
              <div className="skeleton skeleton-title"></div>
              <div className="h-64 skeleton"></div>
            </div>
          </div>
          <div className="card">
            <div className="card-body">
              <div className="skeleton skeleton-title"></div>
              <div className="h-64 skeleton"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const stats = overview?.stats || {};

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-600">
            Real-time overview of your alert intelligence platform
          </p>
        </div>
        <div className="flex space-x-3">
          <button className="btn btn-outline">Export Report</button>
          <button className="btn btn-primary">Configure Alerts</button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Alerts"
          value={stats.activeAlerts || 0}
          change={stats.alertsChange || 0}
          changeType={stats.alertsChangeType || 'increase'}
          icon={BellIcon}
          color="blue"
        />
        <StatCard
          title="Active Incidents"
          value={stats.activeIncidents || 0}
          change={stats.incidentsChange || 0}
          changeType={stats.incidentsChangeType || 'decrease'}
          icon={ExclamationTriangleIcon}
          color="red"
        />
        <StatCard
          title="Services Monitored"
          value={stats.servicesCount || 0}
          change={stats.servicesChange || 0}
          changeType="neutral"
          icon={ServerIcon}
          color="green"
        />
        <StatCard
          title="System Health"
          value={`${stats.systemHealth || 0}%`}
          change={stats.healthChange || 0}
          changeType={stats.healthChangeType || 'increase'}
          icon={ChartBarIcon}
          color="purple"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Alert Trends Chart */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Alert Trends (24h)</h3>
          </div>
          <div className="card-body">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={alertTrends?.data || []}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis 
                    dataKey="time" 
                    tick={{ fontSize: 12 }}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line 
                    type="monotone" 
                    dataKey="count" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Incident Severity Distribution */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Incident Severity</h3>
          </div>
          <div className="card-body">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={incidentTrends?.severityDistribution || []}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {(incidentTrends?.severityDistribution || []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Incidents */}
        <div className="lg:col-span-2">
          <RecentIncidents />
        </div>

        {/* Service Health */}
        <div>
          <ServiceHealth />
        </div>
      </div>

      {/* Alert Severity Chart */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Alert Severity Breakdown</h3>
        </div>
        <div className="card-body">
          <AlertSeverityChart />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
