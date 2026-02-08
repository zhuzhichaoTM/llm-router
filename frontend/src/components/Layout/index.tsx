import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  DashboardOutlined,
  SettingOutlined,
  DollarOutlined,
  ApiOutlined,
  ThunderboltOutlined,
  FileTextOutlined,
  KeyOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { Layout, Menu, Button, Typography } from 'antd';
import type { MenuProps } from 'antd';
const { Title } = Typography;

const menuItems: MenuProps['items'] = [
  {
    key: '/dashboard',
    icon: <DashboardOutlined />,
    label: <Link to="/dashboard">仪表盘</Link>,
  },
  {
    key: '/providers',
    icon: <SettingOutlined />,
    label: <Link to="/providers">Provider 配置</Link>,
  },
  {
    key: '/routing',
    icon: <ThunderboltOutlined />,
    label: <Link to="/routing">路由配置</Link>,
  },
  {
    key: '/cost',
    icon: <DollarOutlined />,
    label: <Link to="/cost">成本分析</Link>,
  },
  {
    key: '/monitor',
    icon: <FileTextOutlined />,
    label: <Link to="/monitor">监控面板</Link>,
  },
  {
    key: '/analytics',
    icon: <BarChartOutlined />,
    label: <Link to="/analytics">数据分析</Link>,
  },
  {
    type: 'divider',
  },
  {
    key: '/api-docs',
    icon: <ApiOutlined />,
    label: <Link to="/api-docs">API 文档</Link>,
  },
  {
    key: '/quick-start',
    icon: <KeyOutlined />,
    label: <Link to="/quick-start">快速开始</Link>,
  },
];

const siderStyle: React.CSSProperties = {
  overflow: 'auto',
  height: '100vh',
  position: 'fixed',
  left: 0,
  top: 0,
  bottom: 0,
};

const headerStyle: React.CSSProperties = {
  background: '#fff',
  padding: '0 24px',
  display: 'flex',
  alignItems: 'center',
};

const contentStyle: React.CSSProperties = {
  margin: '24px 16px',
  padding: 24,
  minHeight: 280,
  background: '#fff',
  borderRadius: '4px',
};

const logoStyle: React.CSSProperties = {
  height: 64,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  borderBottom: '1px solid #f0f0f0',
};

export default function LayoutComponent() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const getSelectedKey = () => {
    return [location.pathname];
  };

  return (
    <Layout style={{ minHeight: '100vh', display: 'flex', flexDirection: 'row' }}>
      <Layout.Sider
        style={siderStyle}
        trigger={null}
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
      >
        <div style={logoStyle}>
          <Title level={4} style={{ margin: 0, color: '#fff' }}>
            LLM Router
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKey()}
          items={menuItems}
        />
      </Layout.Sider>
      <Layout style={{ display: 'flex', flexDirection: 'column', flex: 1, marginLeft: collapsed ? 80 : 200 }}>
        <Layout.Header style={headerStyle}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
          />
        </Layout.Header>
        <Layout.Content style={contentStyle}>
          <Outlet />
        </Layout.Content>
      </Layout>
    </Layout>
  );
}