import React from 'react';
import { useQuery } from 'react-query';
import { ServerIcon, CheckCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/outline';
import { fetchServicesHealth } from '../services/api';

function ServiceHealth() {
  const { data: healthData, isLoading } = useQuery(
    'services-health',
    fetchServicesHealth,
    { refetchInterval: 60000 }
  );

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-gray-900">Service Health</h3>
        </div>
        <div className="card-body space-y-3">
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
      </div>
    );
  }

  const services = healthData?.services || [];

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

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="text-lg font-medium text-gray-900">Service Health</h3>
      </div>
      <div className="card-body">
        {services.length === 0 ? (
          <div className="text-center py-8">
            <ServerIcon className="mx-auto h-12 w-12 text-gray-400" />
            <h3 className="mt-2 text-sm font-medium text-gray-900">No services monitored</h3>
            <p className="mt-1 text-sm text-gray-500">
              Start monitoring services to see their health status
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {services.map((service) => (
              <div key={service.name} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg ${getHealthBgColor(service.health_score)}`}>
                    <ServerIcon className={`h-5 w-5 ${getHealthColor(service.health_score)}`} />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{service.name}</p>
                    <p className="text-xs text-gray-500">{service.alert_count} alerts</p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-medium ${getHealthColor(service.health_score)}`}>
                    {service.health_score}%
                  </span>
                  {getHealthIcon(service.health_score)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default ServiceHealth;
