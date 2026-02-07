import { useState, useEffect } from 'react';
import { chatApi } from '@/api/client';
import type { ChatCompletionRequest, ChatCompletionResponse } from '@/types';

interface ChatState {
  loading: boolean;
  response: ChatCompletionResponse | null;
  error: string | null;
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    loading: false,
    response: null,
    error: null,
  });

  const send = async (request: ChatCompletionRequest): Promise<ChatCompletionResponse | null> => {
    setState({ loading: true, response: null, error: null });

    try {
      const result = await chatApi.completions(request);
      setState({ loading: false, response: result, error: null });
      return result;
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || error.message || '请求失败';
      setState({ loading: false, response: null, error: errorMessage });
      return null;
    }
  };

  const reset = () => {
    setState({ loading: false, response: null, error: null });
  };

  return {
    ...state,
    send,
    reset,
  };
}
