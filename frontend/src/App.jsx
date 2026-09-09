import React, { useState } from 'react';
import Layout from './components/Layout';
import Overview from './pages/Overview';
import Alerts from './pages/Alerts';
import Investigations from './pages/Investigations';
import AttackChains from './pages/AttackChains';
import Users from './pages/Users';
import SystemHealth from './pages/SystemHealth';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <Layout activeTab={activeTab} setActiveTab={setActiveTab}>
      {activeTab === 'overview' && <Overview setActiveTab={setActiveTab} />}
      {activeTab === 'alerts' && <Alerts />}
      {activeTab === 'investigations' && <Investigations />}
      {activeTab === 'attackChains' && <AttackChains />}
      {activeTab === 'users' && <Users />}
      {activeTab === 'health' && <SystemHealth />}
    </Layout>
  );
}
