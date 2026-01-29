# Planning Agent

A conversational planning agent that helps you create and refine plans through natural dialogue. Built with LangGraph for robust state management and complex conversation handling without losing context.

## Features

- **Multi-turn Conversations**: Handles 10+ turns easily. Your context is always preserved.
- **Clarifying Questions**: If your request is vague, the agent asks specific questions before creating a plan.
- **Plan Management**: Create, update, and version your plans. Everything is tracked automatically.
- **Session Persistence**: Close the app and come back later. Your work is saved automatically.
- **Templates**: 12+ pre-built templates for common tasks like trips, weddings, website development, etc.
- **Gantt Charts**: Visualise your timeline with interactive HTML charts.
- **Import/Export**: Bring in plans from Trello, CSV, or Markdown. Export to HTML, CSV, JSON, etc.

## Quick Installation

```bash
git clone https://github.com/Sarvesh-GanesanW/PlannerAgent.git
cd PlannerAgent
pip install -r requirements.txt
```

Or use the install script:
```bash
curl -fsSL https://raw.githubusercontent.com/Sarvesh-GanesanW/PlannerAgent/main/install.sh | bash
```

Then:
```bash
plan-agent
```

## Getting Started

### 1. Configure Your LLM

Supports both Amazon Bedrock and Anthropic:

```bash
python main.py config
```

### 2. Start Using It

```bash
python main.py
```

## Example Usage

```
❯ python main.py
Planning Agent | anthropic:claude-sonnet-4-5-20250929 ●

  ❯ I want to plan a trip to Japan

Agent:
I'd be happy to help! To create the best plan for your trip, I need a bit more information:

1. Which cities are you planning to visit?
2. When are you planning to go?
3. What's your approximate budget?

  ❯ Tokyo and Kyoto, March 2025, $5000 budget

Agent:
[Creates plan with 10 steps from the trip template]
💾 Saved: japan_trip_v1_20250128.md

**Japan Trip** (v1) - 0/10 done
Estimated: 2-4 weeks

  ❯ /save
✓ Session saved: abc123def456

  ❯ /exit
```

Later:
```bash
$ python main.py --resume abc123def456
```

## Design Decisions

### Why LangGraph

I chose LangGraph for the agent architecture for several reasons:

- **State Management**: I needed a way to track conversation state across multiple turns. LangGraph's `AgentState` gives me a TypedDict where I can store everything - messages, plan, summary, preferences.

- **Clear Flow**: The workflow is explicit: `context_mgmt → agent → [tools → agent] → END`. No hidden magic. I can see exactly what is happening.

- **Easy to Extend**: When I wanted to add new tools, I just added them to the tools list. The graph handles routing automatically.

### How I Handle Large Conversations

The agent has an 8K token limit. When conversations reach 70% of that (5.6K tokens), context is compressed:

- The last 4 messages are kept in full (for continuity)
- Older messages are summarised by the LLM
- The summary is stored in the state

**Why this approach?** I wanted to balance memory efficiency with context retention. The last few messages are usually the most relevant for understanding what the user wants now.

### Session Storage

I use pickle + gzip for compression. Here's my thinking:

- **JSON was too big**: A session with 100 messages was 185KB in JSON. With compression, it is under 1KB.
- **Auto-compaction**: When saving, if there are more than 20 messages, the recent 20 are kept and the rest summarised.
- **Undo/Redo limited**: Only the last 10 states are stored. More than that felt unnecessary and bloated the file.

### Plan Structure

I designed plans to be flexible:

```python
{
    "title": "Your Plan",
    "steps": [...],
    "version": 1,
    "history": [...],  # Complete audit trail
    "metadata": {
        "dependencies": {...},  # Step relationships
        "milestones": [...],    # Key achievements
        ...
    }
}
```

**Why version tracking?** I wanted users to see how their plans evolved. The history array stores every change with timestamps.

### Tool Separation

I put all tools in `tools.py` and used dependency injection:

- **Testability**: Each tool can be tested in isolation
- **Reusability**: The same tool can be used by the agent or CLI commands
- **Clarity**: Each tool has one job

### Template System

I created 12+ templates because I noticed people often plan similar things. Each template includes:
- Pre-defined steps
- Suggested dependencies (e.g., book flights before hotel)
- Milestone markers

**Why not generate templates with AI?** I wanted reliable, well-thought-out templates. AI-generated steps might miss important things.

## Configuration

### Option 1: Interactive (Recommended)
```bash
python main.py config
```

### Option 2: Environment Variables
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
export AWS_REGION=us-east-1
export AWS_BEARER_TOKEN_BEDROCK=your-token
```

### Option 3: Config File
```bash
mkdir -p ~/.config/plan-agent
cat > ~/.config/plan-agent/config.json << 'EOF'
{
  "provider": "anthropic",
  "anthropic_api_key": "sk-your-key"
}
EOF
```

## Running Tests

40+ tests covering core functionality:

```bash
pytest tests/ -v
```

With coverage:
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
```

## Troubleshooting

**Problem**: "No API key found"
**Solution**: Run `python main.py config`

**Problem**: Session not found
**Solution**: List your sessions with `python main.py --list-sessions`

**Problem**: Want to change LLM mid-chat
**Solution**: Use `/provider bedrock` or `/provider anthropic`
