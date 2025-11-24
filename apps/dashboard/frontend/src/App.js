import React from 'react';
import { ConfigProvider } from 'antd';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  return (
    <ConfigProvider>
      <div className="App">
        <Dashboard />
      </div>
    </ConfigProvider>
  );
}

export default App;