import React, { useState } from 'react';
import { useQuery } from 'react-query';
import {
  ServerIcon,
  MagnifyingGlassIcon,
  ArrowPathIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/outline';
import { 
  fetchServicesHealth, 
  fetchServiceNoiseScores, 
  fetchTopServices 
} from '../services/api';

function Services() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMetric, setSelectedMetric] = useState('alerts');

  const { data: healthData, isLoading: healthLoading } = useQuery(
    'services-health',
    fetchServicesHealth,
    { refetchInterval: 60000 }
  );

  const { data: noiseData, isLoading: noiseLoading } = useQuery(
    'service-noise-scores',
    fetchServiceNoiseScores,
    { refetchInterval: 300000 }
  );

  const { data: topServices, isLoading: topLoading } = useQuery(
    ['top-services', selectedMetric],
    () => fetchTopServices(selectedMetric, 10),
    { refetchInterval: 60000 }
  );

  const services = healthData?.services || [];
  const noiseScores = noiseData?.services || [];
  const topServicesList = topServices?.services || [];

  const filteredServices = services.filter(service =>
    service.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getNoiseScore = (serviceName) => {
    const noise = noiseScores.find(n => n.service === serviceName);
    return noise?.noise_score || 0;
  };

  const getHealthIcon = (health) => {
    if (health >= 90) {
      return <CheckCircleIcon className="h-5 w-5 text-green-500" />;
    } else if (health >= 70) {
      return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />;
    } else {
      return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />;
    }
  };

  const getHealthColor = (health) => {
    if (health >= 90) return 'text-green-600';
    if (health >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthBgColor = (health) => {
    if (health >= 90) return 'bg-green-100';
    if (health >= 70) return 'bg-yellow-100';
    return 'bg-red-100';
  };

  const getNoiseColor = (score) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-green-600';
  };

  const getNoiseBgColor = (score) => {
    if (score >= 80) return 'bg-red-100';
    if (score >= 60) return 'bg-yellow-100';
    return 'bg-green-100';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Services</h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitor service health, noise scores, and performance metrics
          </p>
        </div>
        <div className="flex space-x-3">
          <button className="btn btn-outline">
            <ArrowPathIcon className="h-4 w-4 mr-2" />
            Refresh
          </button>
          <button className="btn btn-primary">
            Add Service
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="bg-white shadow rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <div className="flex-1">
            <div className="relative">
              <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search services..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="form-input pl-10"
              />
            </div>
          </div>
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="form-input w-48"
          >
            <option value="alerts">Top by Alerts</option>
            <option value="incidents">Top by Incidents</option>
            <option value="noise">Top by Noise</option>
          </select>
        </div>
      </div>

      {/* Services Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services List */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">Service Health</h3>
          </div>
          <div className="card-body">
            {healthLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="skeleton h-8 w-8 rounded"></div>
                      <div className="skeleton skeleton-line w-20"></div>
                    </div>
                    <div className="skeleton skeleton-line w-16"></div>
                  </div>
                ))}
              </div>
            ) : filteredServices.length === 0 ? (
              <div className="text-center py-8">
                <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No services found</h3>
                <p className="mt-1 text-sm text-gray-500">
                  {searchQuery ? 'Try adjusting your search' : 'No services are being monitored'}
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredServices.map((service) => (
                  <div key={service.name} className="flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50">
                    <div className="flex items-center space-x-3">
                      <div className={`p-2 rounded-lg ${getHealthBgColor(service.health_score)}`}>
                        <ServerIcon className={`h-5 w-5 ${getHealthColor(service.health_score)}`} />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{service.name}</p>
                        <p className="text-xs text-gray-500">{service.alert_count} alerts</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-4">
                      <div className="text-right">
                        <span className={`text-sm font-medium ${getHealthColor(service.health_score)}`}>
                          {service.health_score}%
                        </span>
                        <div className="flex items-center">
                          {getHealthIcon(service.health_score)}
                        </div>
                      </div>
                      <div className="text-right">
                        <span className={`text-xs font-medium ${getNoiseColor(getNoiseScore(service.name))}`}>
                          Noise: {getNoiseScore(service.name).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Top Services */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-gray-900">
              Top Services by {selectedMetric.charAt(0).toUpperCase() + selectedMetric.slice(1)}
            </h3>
          </div>
          <div className="card-body">
            {topLoading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="skeleton skeleton-line w-32"></div>
                    <div className="skeleton skeleton-line w-16"></div>
                  </div>
                ))}
              </div>
            ) : topServicesList.length === 0 ? (
              <div className="text-center py-8">
                <ChartBarIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-2 text-sm font-medium text-gray-900">No data available</h3>
                <p className="mt-1 text-sm text-gray-500">
                  No service metrics available for the selected time period
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {topServicesList.map((service, index) => (
                  <div key={service.service} className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary-100 text-primary-600 text-sm font-medium">
                        {index + 1}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">{service.service}</p>
                        <p className="text-xs text-gray-500">
                          {service.alert_count || service.incident_count || service.noise_score} {selectedMetric}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-medium text-gray-900">
                        {service.value || service.score}
                      </span>
                      {selectedMetric === 'noise' && (
                        <span className={`text-xs ${getNoiseColor(service.noise_score)}`}>
                          ({service.noise_score.toFixed(1)}%)
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Noise Score Analysis */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Noise Score Analysis</h3>
        </div>
        <div className="card-body">
          {noiseLoading ? (
            <div className="h-64 skeleton rounded"></div>
          ) : noiseScores.length === 0 ? (
            <div className="text-center py-8">
              <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">No noise data available</h3>
              <p className="mt-1 text-sm text-gray-500">
                Noise score analysis will appear once enough alert data is collected
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {noiseScores
                .sort((a, b) => b.noise_score - a.noise_score)
                .slice(0, 8)
                .map((service) => (
                  <div key={service.service} className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-900">{service.service}</span>
                      <span className={`text-sm font-medium ${getNoiseColor(service.noise_score)}`}>
                        {service.noise_score.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          service.noise_score >= 80
                            ? 'bg-red-500'
                            : service.noise_score >= 60
                            ? 'bg-yellow-500'
                            : 'bg-green-500'
                        }`}
                        style={{ width: `${service.noise_score}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-gray-500 mt-2">
                      {service.total_alerts} total alerts
                    </p>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Services;
