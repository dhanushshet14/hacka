import React from 'react';
import { Card, CardContent } from './ui/card';

export default function StatCard({ title, value, icon, trend, trendValue }) {
  const getTrendColor = () => {
    if (!trend) return 'text-slate-500';
    return trend === 'up' ? 'text-emerald-500' : 'text-red-500';
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    
    return trend === 'up' ? (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
    ) : (
      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
    );
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-500">{title}</span>
          {icon && (
            <span className="text-2xl">{icon}</span>
          )}
        </div>
        <div className="flex items-end">
          <span className="text-3xl font-bold">{value}</span>
          {trend && trendValue && (
            <div className={`ml-2 flex items-center ${getTrendColor()}`}>
              {getTrendIcon()}
              <span className="ml-1 text-sm">{trendValue}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
} 