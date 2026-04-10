import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [alerts, setAlerts] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [overview, setOverview] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [alertsRes, incidentsRes, overviewRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/v1/alerts`),
        axios.get(`${API_BASE_URL}/api/v1/incidents`),
        axios.get(`${API_BASE_URL}/api/v1/dashboard/overview`)
      ]);

      setAlerts(alertsRes.data.alerts || []);
      setIncidents(incidentsRes.data.incidents || []);
      setOverview(overviewRes.data || {});
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const createSampleData = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/v1/sample-data`);
      loadData();
    } catch (error) {
      console.error('Error creating sample data:', error);
    }
  };

  const createAlert = async () => {
    try {
      const newAlert = {
        source: 'demo',
        service: 'demo-service',
        severity: 'medium',
        description: 'Demo alert created from UI',
        tags: ['demo', 'ui']
      };
      await axios.post(`${API_BASE_URL}/api/v1/alerts`, newAlert);
      loadData();
    } catch (error) {
      console.error('Error creating alert:', error);
    }
  };

  const createIncident = async () => {
    try {
      const newIncident = {
        title: 'Demo Incident',
        description: 'Demo incident created from UI',
        severity: 'medium',
        service: 'demo-service'
      };
      await axios.post(`${API_BASE_URL}/api/v1/incidents`, newIncident);
      loadData();
    } catch (error) {
      console.error('Error creating incident:', error);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="text-lg">Loading Alert Intelligence Platform...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-gray-900">Alert Intelligence Platform</h1>
            <div className="flex space-x-4">
              <button
                onClick={createSampleData}
                className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
              >
                Create Sample Data
              </button>
              <button
                onClick={createAlert}
                className="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
              >
                Create Alert
              </button>
              <button
                onClick={createIncident}
                className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
              >
                Create Incident
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-sm font-medium text-gray-500">Total Alerts</h3>
            <p className="text-2xl font-bold text-gray-900">{overview.total_alerts || 0}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-sm font-medium text-gray-500">Total Incidents</h3>
            <p className="text-2xl font-bold text-gray-900">{overview.total_incidents || 0}</p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-sm font-medium text-gray-500">Critical Alerts</h3>
            <p className="text-2xl font-bold text-red-600">
              {overview.severity_distribution?.critical || 0}
            </p>
          </div>
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-sm font-medium text-gray-500">Active Incidents</h3>
            <p className="text-2xl font-bold text-orange-600">
              {overview.active_incidents?.length || 0}
            </p>
          </div>
        </div>

        {/* Recent Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-medium text-gray-900">Recent Alerts</h2>
            </div>
            <div className="p-6">
              {alerts.length === 0 ? (
                <p className="text-gray-500">No alerts found. Create some sample data!</p>
              ) : (
                <div className="space-y-4">
                  {alerts.slice(-5).reverse().map((alert) => (
                    <div key={alert.id} className="border-l-4 border-blue-500 pl-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium text-gray-900">{alert.description}</h4>
                          <p className="text-sm text-gray-500">
                            {alert.service} - {alert.source}
                          </p>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded ${
                          alert.severity === 'critical' ? 'bg-red-100 text-red-800' :
                          alert.severity === 'high' ? 'bg-orange-100 text-orange-800' :
                          alert.severity === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {alert.severity}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recent Incidents */}
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b">
              <h2 className="text-lg font-medium text-gray-900">Recent Incidents</h2>
            </div>
            <div className="p-6">
              {incidents.length === 0 ? (
                <p className="text-gray-500">No incidents found. Create some sample data!</p>
              ) : (
                <div className="space-y-4">
                  {incidents.slice(-5).reverse().map((incident) => (
                    <div key={incident.id} className="border-l-4 border-orange-500 pl-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <h4 className="font-medium text-gray-900">{incident.title}</h4>
                          <p className="text-sm text-gray-500">{incident.service}</p>
                        </div>
                        <span className={`px-2 py-1 text-xs rounded ${
                          incident.status === 'open' ? 'bg-red-100 text-red-800' :
                          incident.status === 'investigating' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {incident.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* API Documentation Link */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-lg font-medium text-blue-900 mb-2">API Documentation</h3>
          <p className="text-blue-700">
            View the full API documentation at{' '}
            <a href={`${API_BASE_URL}/docs`} target="_blank" rel="noopener noreferrer" className="underline">
              {API_BASE_URL}/docs
            </a>
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
