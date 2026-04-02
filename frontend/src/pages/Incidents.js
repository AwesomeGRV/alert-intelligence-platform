import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import {
  ExclamationTriangleIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  PlusIcon,
  ClockIcon,
  UserIcon
} from '@heroicons/react/outline';
import { fetchIncidents } from '../services/api';
import { formatTimestamp, formatDuration, getSeverityColor, getStatusColor } from '../services/api';

function Incidents() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    status: '',
    severity: '',
    service: ''
  });

  const { data: incidents, isLoading, refetch } = useQuery(
    ['incidents', filters],
    () => fetchIncidents(filters),
    { refetchInterval: 30000 }
  );

  const filteredIncidents = incidents?.filter(incident => 
    incident.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    incident.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    incident.service.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Incidents</h1>
          <p className="mt-1 text-sm text-gray-600">
            Track and manage incident response and resolution
          </p>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={() => refetch()}
            className="btn btn-outline"
          >
            <ArrowPathIcon className="h-4 w-4 mr-2" />
            Refresh
          </button>
          <button className="btn btn-primary">
            <PlusIcon className="h-4 w-4 mr-2" />
            Create Incident
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search incidents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input pl-10"
              />
            </div>
          </div>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="form-input"
          >
            <option value="">All Statuses</option>
            <option value="active">Active</option>
            <option value="investigating">Investigating</option>
            <option value="identified">Identified</option>
            <option value="monitoring">Monitoring</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <select
            value={filters.severity}
            onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
            className="form-input"
          >
            <option value="">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Incidents List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="min-w-full divide-y divide-gray-200">
          <div className="bg-gray-50 px-6 py-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">
                {filteredIncidents.length} incidents
              </h3>
              <div className="flex space-x-2">
                <button className="text-sm text-primary-600 hover:text-primary-500">
                  Export
                </button>
                <button className="text-sm text-primary-600 hover:text-primary-500">
                  Bulk Actions
                </button>
              </div>
            </div>
          </div>

          {isLoading ? (
            <div className="divide-y divide-gray-200">
              {[...Array(10)].map((_, i) => (
                <div key={i} className="px-6 py-4">
                  <div className="flex items-center space-x-3">
                    <div className="skeleton h-10 w-10 rounded-full"></div>
                    <div className="flex-1">
                      <div className="skeleton skeleton-line w-3/4"></div>
                      <div className="skeleton skeleton-line w-1/2"></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredIncidents.length === 0 ? (
            <div className="text-center py-12">
              <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No incidents found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchQuery || filters.status || filters.severity
                  ? 'Try adjusting your search or filters'
                  : 'No incidents have been created'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredIncidents.map((incident) => (
                <div key={incident.cluster_id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="flex-shrink-0">
                        <div className={`h-10 w-10 rounded-full flex items-center justify-center bg-${getSeverityColor(incident.severity)}-100`}>
                          <ExclamationTriangleIcon className={`h-6 w-6 text-${getSeverityColor(incident.severity)}-600`} />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <Link
                            to={`/incidents/${incident.cluster_id}`}
                            className="text-sm font-medium text-gray-900 hover:text-primary-600 truncate"
                          >
                            {incident.title}
                          </Link>
                          <span className={`badge badge-${getSeverityColor(incident.severity)}`}>
                            {incident.severity}
                          </span>
                          <span className={`badge badge-${getStatusColor(incident.status)}`}>
                            {incident.status}
                          </span>
                        </div>
                        <p className="mt-1 text-sm text-gray-600 line-clamp-2">
                          {incident.description}
                        </p>
                        <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500">
                          <span>{incident.service}</span>
                          <span className="flex items-center">
                            <ClockIcon className="h-4 w-4 mr-1" />
                            {formatDuration(
                              Math.floor((new Date() - new Date(incident.created_at)) / 60000)
                            )}
                          </span>
                          <span>{incident.alert_count} alerts</span>
                          {incident.assigned_to && (
                            <span className="flex items-center">
                              <UserIcon className="h-4 w-4 mr-1" />
                              {incident.assigned_to}
                            </span>
                          )}
                        </div>
                        {incident.affected_services.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {incident.affected_services.slice(0, 3).map((service) => (
                              <span key={service} className="badge badge-gray text-xs">
                                {service}
                              </span>
                            ))}
                            {incident.affected_services.length > 3 && (
                              <span className="badge badge-gray text-xs">
                                +{incident.affected_services.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-500">
                        {formatTimestamp(incident.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Incidents;
