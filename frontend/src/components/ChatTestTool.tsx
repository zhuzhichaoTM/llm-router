import React, { useState } from 'react';
import { Input, Button, Form, Modal, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ChatCompletionRequest } from '@/types';
import { chatApi } from '@/api/client';

const messageItemStyle: React.CSSProperties = {
  marginBottom: '8px',
  padding: '8px',
  border: '1px solid #d9d9d9',
  borderRadius: '4px',
};

const roleLabelStyle: React.CSSProperties = {
  color: '#8c8c8c',
  fontSize: '12px',
};

const contentStyle: React.CSSProperties = {
  color: '#434343',
};

const headingStyle: React.CSSProperties = {
  fontWeight: 500,
  marginBottom: '8px',
};

const preStyle: React.CSSProperties = {
  background: '#f5f5f5',
  padding: '16px',
  borderRadius: '4px',
  fontSize: '12px',
  overflow: 'auto',
  maxHeight: '256px',
};

const historyContainerStyle: React.CSSProperties = {
  maxHeight: '192px',
  overflowY: 'auto',
  border: '1px solid #d9d9d9',
  borderRadius: '4px',
};

const historyItemStyle: React.CSSProperties = {
  padding: '12px',
  borderBottom: '1px solid #f0f0f0',
  cursor: 'pointer',
};

const historyItemHoverStyle: React.CSSProperties = {
  ...historyItemStyle,
  background: '#fafafa',
};

const flexBetweenStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const timeStyle: React.CSSProperties = {
  fontSize: '12px',
  color: '#8c8c8c',
};

const modelTagStyle: React.CSSProperties = {
  fontSize: '11px',
  background: '#e6f7ff',
  color: '#1890ff',
  padding: '2px 8px',
  borderRadius: '4px',
};

export default function ChatTestTool() {
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = useState<ChatCompletionRequest>({
    model: 'gpt-3.5-turbo',
    messages: [{ role: 'user', content: '' }],
    temperature: 0.7,
    max_tokens: undefined,
    stream: false,
  });
  const [response, setResponse] = useState<string | null>(null);
  const [history, setHistory] = useState<Array<{ request: any; response: string; time: string }>>([]);

  const handleAddMessage = () => {
    setForm({
      ...form,
      messages: [...form.messages, { role: 'user', content: '' }],
    });
  };

  const handleSend = async () => {
    if (!form.messages[form.messages.length - 1].content.trim()) {
      message.warning('请输入消息内容');
      return;
    }

    setLoading(true);
    try {
      const result = await chatApi.completions(form);
      setResponse(JSON.stringify(result, null, 2));

      // Add to history
      setHistory([
        { request: form, response: JSON.stringify(result, null, 2), time: new Date().toLocaleTimeString() },
        ...history,
      ]);

      // Clear input
      setForm({
        ...form,
        messages: [{ role: 'user', content: '' }],
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Button
        type="primary"
        icon={<PlusOutlined />}
        onClick={() => setVisible(true)}
      >
        API 测试工具
      </Button>

      <Modal
        title="在线 API 测试"
        open={visible}
        onCancel={() => setVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setVisible(false)}>
            关闭
          </Button>,
          <Button
            key="send"
            type="primary"
            loading={loading}
            onClick={handleSend}
          >
            发送请求
          </Button>,
        ]}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <Form layout="vertical">
              <Form.Item label="模型">
                <Input
                  value={form.model}
                  onChange={(e) => setForm({ ...form, model: e.target.value })}
                />
              </Form.Item>
              <Form.Item label="消息列表">
                {form.messages.map((msg, index) => (
                  <div key={index} style={messageItemStyle}>
                    <span style={roleLabelStyle}>{msg.role}: </span>
                    {msg.role === 'user' && index === form.messages.length - 1 ? (
                      <Input.TextArea
                        value={msg.content}
                        onChange={(e) => {
                          const newMessages = [...form.messages];
                          newMessages[index] = { ...newMessages[index], content: e.target.value };
                          setForm({ ...form, messages: newMessages });
                        }}
                        placeholder="输入测试消息..."
                        autoSize={{ minRows: 1, maxRows: 4 }}
                      />
                    ) : (
                      <div style={contentStyle}>{msg.content}</div>
                    )}
                  </div>
                ))}
                <Button
                  type="dashed"
                  block
                  onClick={handleAddMessage}
                  style={{ marginTop: '8px' }}
                >
                  + 添加消息
                </Button>
              </Form.Item>
            </Form>
          </div>

          {response && (
            <div>
              <h4 style={headingStyle}>响应结果：</h4>
              <pre style={preStyle}>
                {response}
              </pre>
            </div>
          )}

          {history.length > 0 && (
            <div>
              <h4 style={headingStyle}>历史记录：</h4>
              <div style={historyContainerStyle}>
                {history.map((item, index) => (
                  <div
                    key={index}
                    style={historyItemStyle}
                    onMouseEnter={(e) => Object.assign(e.currentTarget.style, historyItemHoverStyle)}
                    onMouseLeave={(e) => Object.assign(e.currentTarget.style, historyItemStyle)}
                  >
                    <div style={flexBetweenStyle}>
                      <span style={timeStyle}>{item.time}</span>
                      <span style={modelTagStyle}>
                        {item.request.model}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}
