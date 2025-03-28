import React from 'react';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';

export default function UserProfileCard({ user }) {
  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center rounded-full bg-sky-100 w-10 h-10 text-sky-600 font-bold text-lg">
            {user.name.charAt(0)}
          </span>
          <span>{user.name}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          <div>
            <p className="text-sm text-slate-500">Email</p>
            <p className="font-medium">{user.email}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Membership</p>
            <p className="font-medium">{user.membership || 'Standard'}</p>
          </div>
          <div>
            <p className="text-sm text-slate-500">Projects</p>
            <p className="font-medium">{user.projectCount || 0} active projects</p>
          </div>
        </div>
      </CardContent>
      <CardFooter className="flex justify-between">
        <Button variant="outline" size="sm">Edit Profile</Button>
        <Button variant="ghost" size="sm">View Activity</Button>
      </CardFooter>
    </Card>
  );
} 