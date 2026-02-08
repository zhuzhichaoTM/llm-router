"""
Token counter for streaming (Stage 1).

Counts tokens during streaming to provide accurate cost tracking.
"""
import asyncio
from typing import Dict, Optional
from collections import defaultdict
from datetime import datetime, timezone


class TokenCounter:
    """
    Token counter for streaming responses.

    Supports:
    - Multiple concurrent streams
    - Real-time token counting
    - Stream interruption handling
    """

    _instance: Optional["TokenCounter"] = None

    def __new__(cls) -> "TokenCounter":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize token counter."""
        self._initialized = False
        self._streams: Dict[str, Dict] = {}
        self._current_stream_id: Optional[str] = None

    def initialize(self) -> None:
        """Initialize the token counter."""
        self._initialized = True

    def start_stream(
        self,
        stream_id: str,
    ) -> None:
        """
        Start a new streaming session.

        Args:
            stream_id: Unique stream identifier

        Returns:
            None
        """
        if self._current_stream_id is not None:
            raise RuntimeError(f"Another stream is active: {self._current_stream_id}")

        self._streams[stream_id] = {
            "input_count": 0,
            "output_count": 0,
            "total_count": 0,
            "paused": False,
        }
        self._current_stream_id = stream_id

    def add_input(
        self,
        tokens: int,
    ) -> None:
        """
        Add input tokens to current stream.

        Args:
            tokens: Number of input tokens

        Returns:
            None
        """
        stream_id = self._current_stream_id
        if stream_id is None:
            raise RuntimeError("No active stream")

        self._streams[stream_id]["input_count"] += tokens
        self._streams[stream_id]["total_count"] += tokens

    def add_output(
        self,
        tokens: int,
        stream_id: Optional[str] = None,
    ) -> None:
        """
        Add output tokens to a stream.

        Args:
            tokens: Number of output tokens
            stream_id: Stream ID (uses current if None)

        Returns:
            None
        """
        if stream_id is None:
            stream_id = self._current_stream_id

        self._streams[stream_id]["output_count"] += tokens
        self._streams[stream_id]["total_count"] += tokens

    def add_tokens(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """
        Add both input and output tokens.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            None
        """
        stream_id = self._current_stream_id
        if stream_id is None:
            raise RuntimeError("No active stream")

        self.add_input(input_tokens)
        self.add_output(output_tokens)

    def pause_stream(
        self,
        stream_id: str,
    ) -> None:
        """
        Pause a stream.

        Args:
            stream_id: Stream ID to pause

        Returns:
            None
        """
        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")

        self._streams[stream_id]["paused"] = True

    def resume_stream(
        self,
        stream_id: str,
    ) -> None:
        """
        Resume a paused stream.

        Args:
            stream_id: Stream ID to resume

        Returns:
            None
        """
        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")

        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")

        self._streams[stream_id]["paused"] = False

    def is_stream_paused(
        self,
        stream_id: str,
    ) -> bool:
        """
        Check if a stream is paused.

        Args:
            stream_id: Stream ID to check

        Returns:
            bool: True if paused
        """
        if stream_id not in self._streams:
            return False

        return self._streams[stream_id].get("paused", False)

    def get_counts(
        self,
        stream_id: str,
    ) -> Dict[str, int]:
        """
        Get token counts for a stream.

        Args:
            stream_id: Stream ID

        Returns:
            Dict with input_count, output_count, total_count
        """
        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")

        return self._streams[stream_id]

    def end_stream(
        self,
        stream_id: str,
        save_to_db: bool = True,
    ) -> Dict[str, int]:
        """
        End a streaming session.

        Args:
            stream_id: Stream ID to end
            save_to_db: Whether to save to database

        Returns:
            Dict with final token counts
        """
        if stream_id not in self._streams:
            raise KeyError(f"Unknown stream: {stream_id}")

        counts = self.get_counts(stream_id)

        if self._current_stream_id == stream_id:
            self._current_stream_id = None

        # Note: Database saving is handled by caller

        del self._streams[stream_id]

        return counts

    def end_current_stream(
        self,
        save_to_db: bool = True,
    ) -> Optional[Dict[str, int]]:
        """
        End the current active stream.

        Args:
            save_to_db: Whether to save to database

        Returns:
            Dict with final token counts, or None if no stream is active
        """
        if self._current_stream_id is None:
            return None

        stream_id = self._current_stream_id
        counts = self.end_stream(stream_id, save_to_db)

        self._current_stream_id = None

        return counts

    def get_current_counts(self) -> Optional[Dict[str, int]]:
        """
        Get counts for the current active stream.

        Returns:
            Dict with counts, or None if no active stream
        """
        if self._current_stream_id is None:
            return None

        return self.get_counts(self._current_stream_id)

    def get_all_counts(self) -> Dict[str, Dict[str, int]]:
        """
        Get counts for all active streams.

        Returns:
            Dict mapping stream_id to counts
        """
        active_streams = {
            sid: counts
            for sid, counts in self._streams.items()
        }
        return active_streams

    async def close_all(self) -> None:
        """
        Close all streaming sessions and clean up resources.
        """
        self._streams.clear()
        self._current_stream_id = None


# Global instance
token_counter = TokenCounter()
