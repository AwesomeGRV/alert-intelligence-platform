import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import {
  BellIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowPathIcon,
  EyeIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/outline';
import { fetchAlerts, deleteAlert } from '../services/api';
import { formatTimestamp, getSeverityColor, getStatusColor } from '../services/api';
import toast from 'react-hot-toast';

function Alerts() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    service: '',
    severity: '',
    status: ''
  });

  const { data: alerts, isLoading, refetch } = useQuery(
    ['alerts', filters],
    () => fetchAlerts(filters),
    { refetchInterval: 30000 }
  );

  const handleDelete = async (alertId) => {
    if (window.confirm('Are you sure you want to delete this alert?')) {
      try {
        await deleteAlert(alertId);
        toast.success('Alert deleted successfully');
        refetch();
      } catch (error) {
        toast.error('Failed to delete alert');
      }
    }
  };

  const filteredAlerts = alerts?.filter(alert => 
    alert.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
    alert.service.toLowerCase().includes(searchQuery.toLowerCase()) ||
    alert.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
  ) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Alerts</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor and manage alerts from all your services
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
            Create Alert
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
                placeholder="Search alerts..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input pl-10"
              />
            </div>
          </div>
          <select
            value={filters.service}
            onChange={(e) => setFilters({ ...filters, service: e.target.value })}
            className="form-input"
          >
            <option value="">All Services</option>
            <option value="api-gateway">API Gateway</option>
            <option value="user-service">User Service</option>
            <option value="payment-service">Payment Service</option>
            <option value="notification-service">Notification Service</option>
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
            <option value="info">Info</option>
          </select>
        </div>
      </div>

      {/* Alerts List */}
      <div className="bg-white shadow rounded-lg overflow-hidden">
        <div className="min-w-full divide-y divide-gray-200">
          <div className="bg-gray-50 px-6 py-3">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-gray-900">
                {filteredAlerts.length} alerts
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
          ) : filteredAlerts.length === 0 ? (
            <div className="text-center py-12">
              <BellIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No alerts found</h3>
              <p className="mt-1 text-sm text-gray-500">
                {searchQuery || filters.service || filters.severity
                  ? 'Try adjusting your search or filters'
                  : 'No alerts have been generated'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredAlerts.map((alert) => (
                <div key={alert.alert_id} className="px-6 py-4 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3 flex-1">
                      <div className="flex-shrink-0">
                        <div className={`h-10 w-10 rounded-full flex items-center justify-center bg-${getSeverityColor(alert.severity)}-100`}>
                          <BellIcon className={`h-6 w-6 text-${getSeverityColor(alert.severity)}-600`} />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            {alert.description}
                          </p>
                          <span className={`badge badge-${getSeverityColor(alert.severity)}`}>
                            {alert.severity}
                          </span>
                          <span className={`badge badge-${getStatusColor(alert.status)}`}>
                            {alert.status}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                          <span>{alert.service}</span>
                          <span>{alert.source}</span>
                          <span>{formatTimestamp(alert.timestamp)}</span>
                          {alert.dedup_count > 0 && (
                            <span className="text-yellow-600">
                              {alert.dedup_count} duplicates
                            </span>
                          )}
                        </div>
                        {alert.tags.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {alert.tags.slice(0, 3).map((tag) => (
                              <span key={tag} className="badge badge-gray text-xs">
                                {tag}
                              </span>
                            ))}
                            {alert.tags.length > 3 && (
                              <span className="badge badge-gray text-xs">
                                +{alert.tags.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <EyeIcon className="h-5 w-5" />
                      </button>
                      <button className="p-1 text-gray-400 hover:text-gray-600">
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button 
                        onClick={() => handleDelete(alert.alert_id)}
                        className="p-1 text-gray-400 hover:text-red-600"
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
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

export default Alerts;
