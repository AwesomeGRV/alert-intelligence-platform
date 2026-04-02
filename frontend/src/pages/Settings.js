import React, { useState } from 'react';
import {
  CogIcon,
  BellIcon,
  ShieldCheckIcon,
  ServerIcon,
  ChartBarIcon,
  UserGroupIcon
} from '@heroicons/react/outline';

function Settings() {
  const [activeTab, setActiveTab] = useState('general');
  const [settings, setSettings] = useState({
    general: {
      platformName: 'Alert Intelligence Platform',
      timezone: 'UTC',
      dateFormat: 'MM/DD/YYYY',
      refreshInterval: 30
    },
    alerts: {
      autoDeduplication: true,
      dedupWindow: 5,
      clusteringEnabled: true,
      clusteringThreshold: 0.8,
      maxAlertsPerCluster: 100
    },
    notifications: {
      emailNotifications: true,
      slackNotifications: true,
      teamsNotifications: false,
      criticalAlertsOnly: false,
      notificationCooldown: 15
    },
    integrations: {
      newRelicEnabled: false,
      prometheusEnabled: true,
      cloudWatchEnabled: false,
      pagerDutyEnabled: false
    },
    sla: {
      defaultSlaMinutes: 60,
      criticalSlaMinutes: 15,
      highSlaMinutes: 30,
      mediumSlaMinutes: 120,
      lowSlaMinutes: 240
    },
    users: {
      twoFactorAuth: true,
      sessionTimeout: 8,
      maxConcurrentSessions: 3
    }
  });

  const tabs = [
    { id: 'general', name: 'General', icon: CogIcon },
    { id: 'alerts', name: 'Alerts', icon: BellIcon },
    { id: 'notifications', name: 'Notifications', icon: BellIcon },
    { id: 'integrations', name: 'Integrations', icon: ServerIcon },
    { id: 'sla', name: 'SLA', icon: ChartBarIcon },
    { id: 'users', name: 'Users & Security', icon: ShieldCheckIcon }
  ];

  const handleSettingChange = (category, key, value) => {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  };

  const handleSave = () => {
    // Save settings logic here
    console.log('Saving settings:', settings);
    // Show success message
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'general':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Platform Settings</h3>
              <div className="space-y-4">
                <div>
                  <label className="form-label">Platform Name</label>
                  <input
                    type="text"
                    value={settings.general.platformName}
                    onChange={(e) => handleSettingChange('general', 'platformName', e.target.value)}
                    className="form-input"
                  />
                </div>
                <div>
                  <label className="form-label">Timezone</label>
                  <select
                    value={settings.general.timezone}
                    onChange={(e) => handleSettingChange('general', 'timezone', e.target.value)}
                    className="form-input"
                  >
                    <option value="UTC">UTC</option>
                    <option value="EST">EST</option>
                    <option value="PST">PST</option>
                    <option value="CET">CET</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">Date Format</label>
                  <select
                    value={settings.general.dateFormat}
                    onChange={(e) => handleSettingChange('general', 'dateFormat', e.target.value)}
                    className="form-input"
                  >
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                  </select>
                </div>
                <div>
                  <label className="form-label">Dashboard Refresh Interval (seconds)</label>
                  <input
                    type="number"
                    value={settings.general.refreshInterval}
                    onChange={(e) => handleSettingChange('general', 'refreshInterval', parseInt(e.target.value))}
                    className="form-input"
                    min="10"
                    max="300"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case 'alerts':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Alert Processing</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Auto Deduplication</label>
                    <p className="text-sm text-gray-500">Automatically deduplicate similar alerts</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('alerts', 'autoDeduplication', !settings.alerts.autoDeduplication)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.alerts.autoDeduplication ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.alerts.autoDeduplication ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>
                
                <div>
                  <label className="form-label">Deduplication Window (minutes)</label>
                  <input
                    type="number"
                    value={settings.alerts.dedupWindow}
                    onChange={(e) => handleSettingChange('alerts', 'dedupWindow', parseInt(e.target.value))}
                    className="form-input"
                    min="1"
                    max="60"
                  />
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Alert Clustering</label>
                    <p className="text-sm text-gray-500">Group related alerts into clusters</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('alerts', 'clusteringEnabled', !settings.alerts.clusteringEnabled)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.alerts.clusteringEnabled ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.alerts.clusteringEnabled ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div>
                  <label className="form-label">Clustering Similarity Threshold</label>
                  <input
                    type="number"
                    value={settings.alerts.clusteringThreshold}
                    onChange={(e) => handleSettingChange('alerts', 'clusteringThreshold', parseFloat(e.target.value))}
                    className="form-input"
                    min="0.1"
                    max="1.0"
                    step="0.1"
                  />
                </div>

                <div>
                  <label className="form-label">Max Alerts per Cluster</label>
                  <input
                    type="number"
                    value={settings.alerts.maxAlertsPerCluster}
                    onChange={(e) => handleSettingChange('alerts', 'maxAlertsPerCluster', parseInt(e.target.value))}
                    className="form-input"
                    min="10"
                    max="1000"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case 'notifications':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Notification Channels</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Email Notifications</label>
                    <p className="text-sm text-gray-500">Send notifications via email</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('notifications', 'emailNotifications', !settings.notifications.emailNotifications)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.notifications.emailNotifications ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.notifications.emailNotifications ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Slack Notifications</label>
                    <p className="text-sm text-gray-500">Send notifications to Slack</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('notifications', 'slackNotifications', !settings.notifications.slackNotifications)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.notifications.slackNotifications ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.notifications.slackNotifications ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Microsoft Teams Notifications</label>
                    <p className="text-sm text-gray-500">Send notifications to Teams</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('notifications', 'teamsNotifications', !settings.notifications.teamsNotifications)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.notifications.teamsNotifications ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.notifications.teamsNotifications ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Critical Alerts Only</label>
                    <p className="text-sm text-gray-500">Only notify for critical alerts</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('notifications', 'criticalAlertsOnly', !settings.notifications.criticalAlertsOnly)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.notifications.criticalAlertsOnly ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.notifications.criticalAlertsOnly ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div>
                  <label className="form-label">Notification Cooldown (minutes)</label>
                  <input
                    type="number"
                    value={settings.notifications.notificationCooldown}
                    onChange={(e) => handleSettingChange('notifications', 'notificationCooldown', parseInt(e.target.value))}
                    className="form-input"
                    min="1"
                    max="60"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case 'integrations':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Alert Sources</h3>
              <div className="space-y-4">
                {Object.entries(settings.integrations).map(([key, enabled]) => (
                  <div key={key} className="flex items-center justify-between p-4 border rounded-lg">
                    <div>
                      <h4 className="text-sm font-medium text-gray-900">
                        {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                      </h4>
                      <p className="text-sm text-gray-500">
                        {key === 'newRelicEnabled' && 'Monitor New Relic alerts'}
                        {key === 'prometheusEnabled' && 'Monitor Prometheus Alertmanager'}
                        {key === 'cloudWatchEnabled' && 'Monitor AWS CloudWatch alarms'}
                        {key === 'pagerDutyEnabled' && 'Monitor PagerDuty incidents'}
                      </p>
                    </div>
                    <button
                      onClick={() => handleSettingChange('integrations', key, !enabled)}
                      className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                        enabled ? 'bg-primary-600' : 'bg-gray-200'
                      }`}
                    >
                      <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                        style={{ transform: enabled ? 'translateX(20px)' : 'translateX(0)' }}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        );

      case 'sla':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Service Level Agreement (SLA)</h3>
              <div className="space-y-4">
                <div>
                  <label className="form-label">Default SLA (minutes)</label>
                  <input
                    type="number"
                    value={settings.sla.defaultSlaMinutes}
                    onChange={(e) => handleSettingChange('sla', 'defaultSlaMinutes', parseInt(e.target.value))}
                    className="form-input"
                    min="15"
                    max="1440"
                  />
                </div>
                <div>
                  <label className="form-label">Critical SLA (minutes)</label>
                  <input
                    type="number"
                    value={settings.sla.criticalSlaMinutes}
                    onChange={(e) => handleSettingChange('sla', 'criticalSlaMinutes', parseInt(e.target.value))}
                    className="form-input"
                    min="5"
                    max="60"
                  />
                </div>
                <div>
                  <label className="form-label">High SLA (minutes)</label>
                  <input
                    type="number"
                    value={settings.sla.highSlaMinutes}
                    onChange={(e) => handleSettingChange('sla', 'highSlaMinutes', parseInt(e.target.value))}
                    className="form-input"
                    min="15"
                    max="120"
                  />
                </div>
                <div>
                  <label className="form-label">Medium SLA (minutes)</label>
                  <input
                    type="number"
                    value={settings.sla.mediumSlaMinutes}
                    onChange={(e) => handleSettingChange('sla', 'mediumSlaMinutes', parseInt(e.target.value))}
                    className="form-input"
                    min="30"
                    max="240"
                  />
                </div>
                <div>
                  <label className="form-label">Low SLA (minutes)</label>
                  <input
                    type="number"
                    value={settings.sla.lowSlaMinutes}
                    onChange={(e) => handleSettingChange('sla', 'lowSlaMinutes', parseInt(e.target.value))}
                    className="form-input"
                    min="60"
                    max="1440"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      case 'users':
        return (
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">User Management & Security</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <label className="form-label">Two-Factor Authentication</label>
                    <p className="text-sm text-gray-500">Require 2FA for all users</p>
                  </div>
                  <button
                    onClick={() => handleSettingChange('users', 'twoFactorAuth', !settings.users.twoFactorAuth)}
                    className={`relative inline-flex flex-shrink-0 h-6 w-11 border-2 border-transparent rounded-full cursor-pointer transition-colors ease-in-out duration-200 focus:outline-none ${
                      settings.users.twoFactorAuth ? 'bg-primary-600' : 'bg-gray-200'
                    }`}
                  >
                    <span className="translate-x-0 inline-block h-5 w-5 rounded-full bg-white shadow transform ring-0 transition ease-in-out duration-200"
                      style={{ transform: settings.users.twoFactorAuth ? 'translateX(20px)' : 'translateX(0)' }}
                    />
                  </button>
                </div>

                <div>
                  <label className="form-label">Session Timeout (hours)</label>
                  <input
                    type="number"
                    value={settings.users.sessionTimeout}
                    onChange={(e) => handleSettingChange('users', 'sessionTimeout', parseInt(e.target.value))}
                    className="form-input"
                    min="1"
                    max="24"
                  />
                </div>

                <div>
                  <label className="form-label">Max Concurrent Sessions</label>
                  <input
                    type="number"
                    value={settings.users.maxConcurrentSessions}
                    onChange={(e) => handleSettingChange('users', 'maxConcurrentSessions', parseInt(e.target.value))}
                    className="form-input"
                    min="1"
                    max="10"
                  />
                </div>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Settings</h1>
          <p className="mt-1 text-sm text-gray-600">
            Configure platform settings and preferences
          </p>
        </div>
        <div className="flex space-x-3">
          <button className="btn btn-outline">
            Reset to Defaults
          </button>
          <button onClick={handleSave} className="btn btn-primary">
            Save Changes
          </button>
        </div>
      </div>

      {/* Settings Layout */}
      <div className="bg-white shadow rounded-lg">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`group inline-flex items-center py-4 px-6 border-b-2 text-sm font-medium ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <Icon className="mr-2 h-5 w-5" />
                  {tab.name}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-6">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
}

export default Settings;
