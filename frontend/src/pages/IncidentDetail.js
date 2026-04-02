import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  ExclamationTriangleIcon,
  ArrowLeftIcon,
  ClockIcon,
  UserIcon,
  ServerIcon,
  CheckCircleIcon,
  PencilIcon,
  TrashIcon
} from '@heroicons/react/outline';
import { 
  fetchIncident, 
  fetchIncidentAlerts, 
  updateIncident, 
  resolveIncident 
} from '../services/api';
import { formatTimestamp, formatDuration, getSeverityColor, getStatusColor } from '../services/api';
import toast from 'react-hot-toast';

function IncidentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({});

  const { data: incident, isLoading: incidentLoading } = useQuery(
    ['incident', id],
    () => fetchIncident(id),
    { enabled: !!id }
  );

  const { data: alerts, isLoading: alertsLoading } = useQuery(
    ['incident-alerts', id],
    () => fetchIncidentAlerts(id, 50),
    { enabled: !!id }
  );

  const updateMutation = useMutation(updateIncident, {
    onSuccess: () => {
      queryClient.invalidateQueries(['incident', id]);
      toast.success('Incident updated successfully');
      setIsEditing(false);
    },
    onError: () => {
      toast.error('Failed to update incident');
    }
  });

  const resolveMutation = useMutation(resolveIncident, {
    onSuccess: () => {
      queryClient.invalidateQueries(['incident', id]);
      toast.success('Incident resolved successfully');
    },
    onError: () => {
      toast.error('Failed to resolve incident');
    }
  });

  const handleEdit = () => {
    setEditForm({
      title: incident.title,
      description: incident.description,
      severity: incident.severity,
      assigned_to: incident.assigned_to || ''
    });
    setIsEditing(true);
  };

  const handleSave = () => {
    updateMutation.mutate({ id, ...editForm });
  };

  const handleResolve = () => {
    const rootCause = prompt('What is the root cause of this incident?');
    const fix = prompt('What fix was applied?');
    
    if (rootCause && fix) {
      resolveMutation.mutate({ 
        id, 
        root_cause: rootCause, 
        fix: fix 
      });
    }
  };

  if (incidentLoading || alertsLoading) {
    return (
      <div className="space-y-6">
        <div className="skeleton skeleton-title w-1/3"></div>
        <div className="card">
          <div className="card-body">
            <div className="skeleton skeleton-line w-2/3"></div>
            <div className="skeleton skeleton-line w-1/2"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="text-center py-12">
        <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-gray-400" />
        <h3 className="mt-2 text-sm font-medium text-gray-900">Incident not found</h3>
        <p className="mt-1 text-sm text-gray-500">
          The incident you're looking for doesn't exist.
        </p>
        <button
          onClick={() => navigate('/incidents')}
          className="mt-4 btn btn-primary"
        >
          Back to Incidents
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => navigate('/incidents')}
            className="p-2 text-gray-400 hover:text-gray-600"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </button>
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {isEditing ? (
                <input
                  type="text"
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="form-input"
                />
              ) : (
                incident.title
              )}
            </h1>
            <div className="mt-1 flex items-center space-x-2">
              <span className={`badge badge-${getSeverityColor(incident.severity)}`}>
                {incident.severity}
              </span>
              <span className={`badge badge-${getStatusColor(incident.status)}`}>
                {incident.status}
              </span>
              <span className="text-sm text-gray-500">
                {incident.service}
              </span>
            </div>
          </div>
        </div>
        <div className="flex space-x-3">
          {isEditing ? (
            <>
              <button
                onClick={() => setIsEditing(false)}
                className="btn btn-outline"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={updateMutation.isLoading}
                className="btn btn-primary"
              >
                {updateMutation.isLoading ? 'Saving...' : 'Save'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleEdit}
                className="btn btn-outline"
              >
                <PencilIcon className="h-4 w-4 mr-2" />
                Edit
              </button>
              {incident.status !== 'resolved' && (
                <button
                  onClick={handleResolve}
                  disabled={resolveMutation.isLoading}
                  className="btn btn-success"
                >
                  <CheckCircleIcon className="h-4 w-4 mr-2" />
                  {resolveMutation.isLoading ? 'Resolving...' : 'Resolve'}
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Incident Details */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Description</h3>
            </div>
            <div className="card-body">
              {isEditing ? (
                <textarea
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="form-input"
                  rows={4}
                />
              ) : (
                <p className="text-gray-700">{incident.description}</p>
              )}
            </div>
          </div>

          {/* Timeline */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Timeline</h3>
            </div>
            <div className="card-body">
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-primary-100 flex items-center justify-center">
                      <ExclamationTriangleIcon className="h-4 w-4 text-primary-600" />
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900">Incident Created</p>
                    <p className="text-sm text-gray-500">
                      {formatTimestamp(incident.created_at)}
                    </p>
                  </div>
                </div>
                
                {incident.first_alert_time && (
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-yellow-100 flex items-center justify-center">
                        <ClockIcon className="h-4 w-4 text-yellow-600" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">First Alert</p>
                      <p className="text-sm text-gray-500">
                        {formatTimestamp(incident.first_alert_time)}
                      </p>
                    </div>
                  </div>
                )}

                {incident.resolution_time && (
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0">
                      <div className="h-8 w-8 rounded-full bg-green-100 flex items-center justify-center">
                        <CheckCircleIcon className="h-4 w-4 text-green-600" />
                      </div>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-gray-900">Incident Resolved</p>
                      <p className="text-sm text-gray-500">
                        {formatTimestamp(incident.resolution_time)}
                      </p>
                      <p className="text-sm text-gray-600 mt-1">
                        Time to resolve: {formatDuration(incident.time_to_resolve || 0)}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Related Alerts */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">
                Related Alerts ({alerts?.length || 0})
              </h3>
            </div>
            <div className="card-body">
              {alerts?.length === 0 ? (
                <p className="text-gray-500">No alerts associated with this incident</p>
              ) : (
                <div className="space-y-3">
                  {alerts?.map((alert) => (
                    <div key={alert.alert_id} className="border-l-4 border-gray-200 pl-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-gray-900">
                            {alert.description}
                          </p>
                          <div className="mt-1 flex items-center space-x-2 text-sm text-gray-500">
                            <span>{alert.service}</span>
                            <span>•</span>
                            <span>{formatTimestamp(alert.timestamp)}</span>
                          </div>
                        </div>
                        <span className={`badge badge-${getSeverityColor(alert.severity)}`}>
                          {alert.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Metadata */}
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-gray-900">Metadata</h3>
            </div>
            <div className="card-body space-y-4">
              <div>
                <p className="text-sm font-medium text-gray-900">Incident ID</p>
                <p className="text-sm text-gray-500">{incident.cluster_id}</p>
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-900">Service</p>
                <p className="text-sm text-gray-500">{incident.service}</p>
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-900">Alert Count</p>
                <p className="text-sm text-gray-500">{incident.alert_count}</p>
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-900">Assigned To</p>
                {isEditing ? (
                  <input
                    type="text"
                    value={editForm.assigned_to}
                    onChange={(e) => setEditForm({ ...editForm, assigned_to: e.target.value })}
                    className="form-input mt-1"
                    placeholder="Unassigned"
                  />
                ) : (
                  <p className="text-sm text-gray-500">
                    {incident.assigned_to || 'Unassigned'}
                  </p>
                )}
              </div>
              
              <div>
                <p className="text-sm font-medium text-gray-900">Duration</p>
                <p className="text-sm text-gray-500">
                  {formatDuration(
                    Math.floor((new Date() - new Date(incident.created_at)) / 60000)
                  )}
                </p>
              </div>
            </div>
          </div>

          {/* Affected Services */}
          {incident.affected_services.length > 0 && (
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-medium text-gray-900">Affected Services</h3>
              </div>
              <div className="card-body">
                <div className="space-y-2">
                  {incident.affected_services.map((service) => (
                    <div key={service} className="flex items-center space-x-2">
                      <ServerIcon className="h-4 w-4 text-gray-400" />
                      <span className="text-sm text-gray-700">{service}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Resolution */}
          {incident.resolved_root_cause && (
            <div className="card">
              <div className="card-header">
                <h3 className="text-lg font-medium text-gray-900">Resolution</h3>
              </div>
              <div className="card-body space-y-4">
                <div>
                  <p className="text-sm font-medium text-gray-900">Root Cause</p>
                  <p className="text-sm text-gray-700">{incident.resolved_root_cause}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Fix Applied</p>
                  <p className="text-sm text-gray-700">{incident.fix_applied}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default IncidentDetail;
