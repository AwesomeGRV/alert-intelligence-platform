import React from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { ExclamationTriangleIcon, ClockIcon } from '@heroicons/react/outline';
import { fetchActiveIncidentsSummary } from '../services/api';
import { formatTimestamp, getSeverityColor, getStatusColor } from '../services/api';

function RecentIncidents() {
  const { data: summary, isLoading } = useQuery(
    'active-incidents-summary',
    fetchActiveIncidentsSummary,
    { refetchInterval: 30000 }
  );

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Recent Incidents</h3>
        </div>
        <div className="card-body space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex items-center space-x-3">
              <div className="skeleton h-10 w-10 rounded-full"></div>
              <div className="flex-1">
                <div className="skeleton skeleton-line w-3/4"></div>
                <div className="skeleton skeleton-line w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const recentIncidents = summary?.recent_incidents || [];

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-gray-900">Recent Incidents</h3>
          <Link
            to="/incidents"
            className="text-sm text-primary-600 hover:text-primary-500"
          >
            View all
          </Link>
        </div>
      </div>
      <div className="card-body">
        {recentIncidents.length === 0 ? (
          <div className="text-center py-8">
            <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No active incidents</h3>
            <p className="mt-1 text-sm text-gray-500">
              All systems are operating normally
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {recentIncidents.map((incident) => (
              <div key={incident.cluster_id} className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className={`h-10 w-10 rounded-full flex items-center justify-center bg-${getSeverityColor(incident.severity)}-100`}>
                    <ExclamationTriangleIcon className={`h-6 w-6 text-${getSeverityColor(incident.severity)}-600`} />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/incidents/${incident.cluster_id}`}
                    className="text-sm font-medium text-gray-900 hover:text-gray-600 truncate"
                  >
                    {incident.title}
                  </Link>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className={`badge badge-${getSeverityColor(incident.severity)}`}>
                      {incident.severity}
                    </span>
                    <span className={`badge badge-${getStatusColor('active')}`}>
                      Active
                    </span>
                    <span className="text-xs text-gray-500 flex items-center">
                      <ClockIcon className="h-3 w-3 mr-1" />
                      {formatTimestamp(incident.created_at)}
                    </span>
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <span className="text-sm text-gray-500">{incident.service}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default RecentIncidents;
