# Travel Agent Evaluation Framework

This directory contains evaluation tests for the travel agent using Google ADK's built-in evaluation framework.

## Overview

ADK provides a comprehensive evaluation system with two approaches:

1. **Test Files** (`*.test.json`) - Unit tests for single sessions
2. **Evalset Files** (`*.evalset.json`) - Integration tests for multiple sessions

This example uses **test files** for rapid development and testing.

## Files

- `travel_agent_eval.test.json` - Test cases for core functionality
- `test_config.json` - Evaluation criteria and scoring configuration
- `README.md` - This file

## Test Cases

### 1. Memory Creation (`test_memory_creation`)
Tests that the agent correctly creates memories when user shares preferences.

**Expected behavior:**
- Agent uses `create_memory` tool
- Agent acknowledges user preferences
- Memories are stored for future use

### 2. Memory Recall (`test_memory_recall`)
Tests that the agent recalls user preferences in subsequent conversations.

**Expected behavior:**
- Agent uses `search_memory` tool
- Agent references stored preferences
- Agent personalizes recommendations

### 3. Calendar Export (`test_calendar_export`)
Tests that the agent can export itineraries to ICS format.

**Expected behavior:**
- Agent uses `export_to_calendar` tool
- Agent generates valid ICS content
- Agent provides download instructions

## Evaluation Criteria

The tests use three evaluation criteria (see `test_config.json`):

1. **Tool Trajectory (30%)** - Checks if correct tools are used in order
2. **Response Match (40%)** - LLM judges semantic similarity to expected response
3. **Tool Use Quality (30%)** - LLM evaluates tool usage against rubrics

## Running Evaluations

### Method 1: ADK Web UI (Recommended for Development)

```bash
cd examples/travel_agent_memory
uv run adk web .
```

Then navigate to the "Evaluate" tab in the web interface.

### Method 2: Command Line

```bash
cd examples/travel_agent_memory
uv run adk eval evaluation/travel_agent_eval.test.json \
  --config evaluation/test_config.json \
  --output evaluation/results.json
```

### Method 3: Programmatic (pytest)

```bash
cd examples/travel_agent_memory
uv run pytest evaluation/travel_agent_eval.test.json -v
```

## Interpreting Results

Each test case receives a score from 0.0 to 1.0:

- **1.0** - Perfect match (all criteria met)
- **0.7-0.9** - Good (minor deviations)
- **0.4-0.6** - Fair (some issues)
- **< 0.4** - Poor (significant problems)

The overall score is a weighted average of all criteria.

## Adding New Tests

To add new test cases, edit `travel_agent_eval.test.json`:

```json
{
  "eval_id": "test_new_feature",
  "conversation": [
    {
      "invocation_id": "new-001",
      "user_content": {
        "parts": [{"text": "Your test prompt"}],
        "role": "user"
      },
      "final_response": {
        "parts": [{"text": "Expected response"}],
        "role": "model"
      },
      "intermediate_data": {
        "tool_uses": [
          {"name": "tool_name", "args": {"param": "value"}}
        ]
      }
    }
  ],
  "session_input": {
    "app_name": "travel_agent",
    "user_id": "test_user",
    "state": {}
  }
}
```

## Best Practices

1. **Keep tests focused** - One test per feature/behavior
2. **Use realistic data** - Test with actual user scenarios
3. **Test edge cases** - Include error conditions and unusual inputs
4. **Update regularly** - Add tests when adding new features
5. **Monitor scores** - Track evaluation scores over time

## Troubleshooting

### Tests fail with "Agent not found"
Make sure you're running from the `examples/travel_agent_memory` directory.

### Low tool trajectory scores
Check that `intermediate_data.tool_uses` matches actual agent behavior.

### Low response match scores
Adjust the threshold in `test_config.json` or make expected responses more flexible.

## Learn More

- [ADK Evaluation Docs](https://google.github.io/adk-docs/evaluate/)
- [ADK Test Schema](https://google.github.io/adk-docs/evaluate/test-schema/)
- [Evaluation Criteria](https://google.github.io/adk-docs/evaluate/criteria/)

