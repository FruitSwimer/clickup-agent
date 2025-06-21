# Debug Logging Guide

## Overview

The ClickUp Agent now includes comprehensive debug logging to help trace message flow and diagnose issues.

## Enabling/Disabling Debug Logs

Debug logs are controlled by the `DEBUG_MESSAGES` environment variable:

```bash
# Enable debug logs (default)
export DEBUG_MESSAGES=true

# Disable debug logs
export DEBUG_MESSAGES=false
```

You can also set it in your `.env` file:
```
DEBUG_MESSAGES=true
```

## What Gets Logged

When debug logging is enabled, you'll see:

### 1. Message History
- 🔍 Number of messages retrieved from history
- 📊 Message limit applied
- 📝 Preview of each message content (first 100 chars)
- ➡️ Confirmation of messages sent to AI

### 2. User Input/AI Response
- 📝 User input (first 200 chars)
- 🤖 AI response (first 200 chars)

### 3. Database Operations
- 📦 Number of messages received from agent run
- 🔄 Existing vs new messages count
- ✅ Save/update confirmations
- 📊 Total messages in database after save

### 4. Message Filtering
- 🎯 Applied message limit
- 📤 Number of messages returned after filtering

## Example Output

```
2025-06-20 10:30:45 - src.agent.agent - INFO - 🔍 Message History (limit=15):
2025-06-20 10:30:45 - src.agent.agent - INFO -    Total messages retrieved: 15
2025-06-20 10:30:45 - src.agent.agent - INFO -    [1] ModelRequest: Hello, how are you?
2025-06-20 10:30:45 - src.agent.agent - INFO -    [2] ModelResponse: I'm doing well, thank you! How can I help you today?
...
2025-06-20 10:30:45 - src.agent.agent - INFO -    ➡️  Sending these 15 messages to the AI model

2025-06-20 10:30:45 - src.agent.agent - INFO - 📝 User Input: Can you help me with a task?

2025-06-20 10:30:46 - src.agent.agent - INFO - 🤖 AI Response: Of course! I'd be happy to help...

2025-06-20 10:30:46 - src.agent.agent - INFO - 💾 Saving conversation to database:
2025-06-20 10:30:46 - src.agent.agent - INFO -    Session ID: user123
2025-06-20 10:30:46 - src.agent.agent - INFO -    Total messages in result: 17
2025-06-20 10:30:46 - src.agent.agent - INFO -    New messages to save: 2

2025-06-20 10:30:46 - src.services.message_service - INFO - ✅ Session updated: True
2025-06-20 10:30:46 - src.agent.agent - INFO - ✅ Verification - Total messages now in database: 17
```

## Testing Debug Logs

Run the test script to see debug logging in action:

```bash
python test_debug_logs.py
```

This will:
1. Create a new conversation
2. Add multiple messages
3. Show how message limits work
4. Demonstrate enabling/disabling debug logs

## Performance Considerations

Debug logging has minimal performance impact, but for production environments with high traffic, you may want to disable it:

```bash
export DEBUG_MESSAGES=false
```

## Troubleshooting

If messages aren't being saved correctly:
1. Enable debug logs
2. Check for "✅ Session updated" messages
3. Verify the message counts match expectations
4. Look for any error messages in the logs

If message history seems incorrect:
1. Check the "🔍 Message History" section
2. Verify the limit is being applied correctly
3. Ensure messages are in the correct order