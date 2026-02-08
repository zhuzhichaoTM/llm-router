import React, { useState } from 'react';
import { Modal, Input, Button, Form, message } from 'antd';

export default function ApiKeyModal() {
  const [visible, setVisible] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [adminApiKey, setAdminApiKey] = useState('');
  const [isAdmin, setIsAdmin] = useState(false);

  React.useEffect(() => {
    // Show modal if no API key is set
    const existingKey = localStorage.getItem('llm_router_api_key');
    if (!existingKey) {
      setVisible(true);
    }
  }, []);

  const handleSave = () => {
    if (apiKey) {
      localStorage.setItem('llm_router_api_key', apiKey);
      if (isAdmin && adminApiKey) {
        localStorage.setItem('llm_router_admin_api_key', adminApiKey);
      }
      setVisible(false);
      message.success('API Key 已保存');
    } else {
      message.error('请输入有效的 API Key');
    }
  };

  return (
    <Modal
      title="设置 API Key"
      open={visible}
      onOk={handleSave}
      onCancel={() => setVisible(false)}
      width={500}
    >
      <Form layout="vertical">
        <Form.Item label="API Key" required>
          <Input.Password
            placeholder="输入您的 API Key"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
          />
        </Form.Item>
        <Form.Item>
          <Button
            type="link"
            onClick={() => setIsAdmin(!isAdmin)}
          >
            {isAdmin ? '隐藏' : '显示'} 管理员 API Key
          </Button>
        </Form.Item>
        {isAdmin && (
          <Form.Item label="管理员 API Key">
            <Input.Password
              placeholder="输入管理员 API Key"
              value={adminApiKey}
              onChange={(e) => setAdminApiKey(e.target.value)}
            />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
