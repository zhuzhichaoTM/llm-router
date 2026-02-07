import React from 'react';
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
} from '@ant-design/icons';
import { Layout, Menu, Button, theme, Typography } from 'antd';
import type { MenuProps } from 'antd';
import { LayoutProvider, useLayout } from './Layout';
const { Sider, Content, Header } = Layout;
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
export default function LayoutComponent() {
  const location = useLocation();
  const { collapsed, setCollapsed } = useLayout();
  const {
    token: { colorBgContainer, colorBgLayout },
  } = theme.useToken();
  const getSelectedKey = () => {
    return [location.pathname];
  };
  return (
    <Layout className="min-h-screen">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        onCollapse={(value) => setCollapsed(value)}
        className="shadow-lg"
      >
        <div className="h-16 flex items-center justify-center border-b border-gray-200">
          <Title level={4} className="!m-0 text-primary">
            LLM Router
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={getSelectedKey()}
          items={menuItems}
          className="border-r-0"
        />
      </Sider>
      <Layout>
        <Header className="bg-white shadow-sm px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">API Key:</span>
            <KeyOutlined className="text-gray-400" />
          </div>
        </Header>
        <Content className="bg-gray-50 p-6 overflow-auto">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}