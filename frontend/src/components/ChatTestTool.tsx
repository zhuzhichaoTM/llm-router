import React, { useState } from 'react';
import { Input, Button, Form, Modal, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import type { ChatCompletionRequest, Message } from '@/types';
import { chatApi, setApiKey } from '@/api/client';

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
        <div className="space-y-4">
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
                  <div key={index} className="mb-2 p-2 border rounded">
                    <span className="text-gray-500 text-sm">{msg.role}: </span>
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
                      <div className="text-gray-700">{msg.content}</div>
                    )}
                  </div>
                ))}
                <Button
                  type="dashed"
                  block
                  onClick={handleAddMessage}
                  className="mt-2"
                >
                  + 添加消息
                </Button>
              </Form.Item>
            </Form>
          </div>

          {response && (
            <div>
              <h4 className="font-medium mb-2">响应结果：</h4>
              <pre className="bg-gray-100 p-4 rounded text-xs overflow-auto max-h-64">
                {response}
              </pre>
            </div>
          )}

          {history.length > 0 && (
            <div>
              <h4 className="font-medium mb-2">历史记录：</h4>
              <div className="max-h-48 overflow-y-auto border rounded">
                {history.map((item, index) => (
                  <div
                    key={index}
                    className="p-3 border-b hover:bg-gray-50 cursor-pointer"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-500">{item.time}</span>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
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
