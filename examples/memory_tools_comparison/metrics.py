# Copyright 2025 Google LLC
# Copyright 2025 Redis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Metrics collection for memory comparison examples."""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationMetrics:
    """Metrics collected during a conversation."""

    approach: str  # "tool-based" or "service-based"
    total_messages: int = 0
    total_llm_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_seconds: float = 0.0
    memory_operations: dict[str, int] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    conversation_log: list[dict[str, Any]] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def record_message(self, user_message: str, agent_response: str, latency: float):
        """Record a message exchange."""
        self.total_messages += 1
        self.total_latency_seconds += latency
        self.conversation_log.append({
            "user": user_message,
            "agent": agent_response,
            "latency": latency,
        })

    def record_llm_call(self, input_tokens: int, output_tokens: int):
        """Record an LLM call."""
        self.total_llm_calls += 1
        self.total_tokens_input += input_tokens
        self.total_tokens_output += output_tokens

    def record_memory_operation(self, operation: str):
        """Record a memory operation."""
        if operation not in self.memory_operations:
            self.memory_operations[operation] = 0
        self.memory_operations[operation] += 1

    def record_tool_call(self, tool_name: str, parameters: dict[str, Any], result: Any):
        """Record a tool call."""
        self.tool_calls.append({
            "tool": tool_name,
            "parameters": parameters,
            "result": result,
        })

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of metrics."""
        total_time = time.time() - self.start_time
        return {
            "approach": self.approach,
            "total_messages": self.total_messages,
            "total_llm_calls": self.total_llm_calls,
            "total_tokens": self.total_tokens_input + self.total_tokens_output,
            "input_tokens": self.total_tokens_input,
            "output_tokens": self.total_tokens_output,
            "avg_latency_per_message": (
                self.total_latency_seconds / self.total_messages
                if self.total_messages > 0
                else 0
            ),
            "total_time_seconds": total_time,
            "memory_operations": self.memory_operations,
            "tool_calls_count": len(self.tool_calls),
        }

    def print_summary(self):
        """Print a formatted summary."""
        summary = self.get_summary()
        print(f"\n{'='*60}")
        print(f"Metrics Summary - {self.approach.upper()}")
        print(f"{'='*60}")
        print(f"Total Messages: {summary['total_messages']}")
        print(f"Total LLM Calls: {summary['total_llm_calls']}")
        print(f"Total Tokens: {summary['total_tokens']:,} (Input: {summary['input_tokens']:,}, Output: {summary['output_tokens']:,})")
        print(f"Avg Latency/Message: {summary['avg_latency_per_message']:.2f}s")
        print(f"Total Time: {summary['total_time_seconds']:.2f}s")
        print(f"\nMemory Operations:")
        for op, count in summary['memory_operations'].items():
            print(f"  - {op}: {count}")
        print(f"Tool Calls: {summary['tool_calls_count']}")
        print(f"{'='*60}\n")

