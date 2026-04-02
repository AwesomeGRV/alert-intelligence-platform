import React from 'react';

const StatCard = ({ title, value, change, changeType, icon: Icon, color }) => {
  const getColorClasses = (color) => {
    const colors = {
      blue: {
        bg: 'bg-blue-500',
        lightBg: 'bg-blue-100',
        text: 'text-blue-600',
        changeText: 'text-blue-600'
      },
      red: {
        bg: 'bg-red-500',
        lightBg: 'bg-red-100',
        text: 'text-red-600',
        changeText: 'text-red-600'
      },
      green: {
        bg: 'bg-green-500',
        lightBg: 'bg-green-100',
        text: 'text-green-600',
        changeText: 'text-green-600'
      },
      purple: {
        bg: 'bg-purple-500',
        lightBg: 'bg-purple-100',
        text: 'text-purple-600',
        changeText: 'text-purple-600'
      }
    };
    return colors[color] || colors.blue;
  };

  const colors = getColorClasses(color);

  const getChangeIcon = () => {
    if (changeType === 'increase') {
      return <TrendingUpIcon className="h-4 w-4" />;
    } else if (changeType === 'decrease') {
      return <TrendingDownIcon className="h-4 w-4" />;
    }
    return null;
  };

  const getChangeColor = () => {
    if (changeType === 'increase') {
      return 'text-green-600';
    } else if (changeType === 'decrease') {
      return 'text-red-600';
    }
    return 'text-gray-500';
  };

  return (
    <div className="stat-card">
      <div className="stat-card-content">
        <div className="flex items-center">
          <div className={`flex-shrink-0 ${colors.lightBg} rounded-lg p-3`}>
            <Icon className={`h-6 w-6 ${colors.text}`} aria-hidden="true" />
          </div>
          <div className="ml-5 w-0 flex-1">
            <dl>
              <dt className="stat-card-title">{title}</dt>
              <dd className="stat-card-value">
                {value}
                {change !== undefined && (
                  <span className={`ml-2 inline-flex items-center text-sm font-medium ${getChangeColor()}`}>
                    {getChangeIcon()}
                    {Math.abs(change)}%
                  </span>
                )}
              </dd>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatCard;
