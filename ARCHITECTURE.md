# JARVIS-F.R.D.A.Y — System Architecture

## Full-Stack AI Operating System

### 🧠 Brain Layer
- **spec-kit** — planning engine that breaks tasks into structured specs
- **ARC-KIT** — reasoning engine for multi-step logical inference
- **prompt-master** — self-optimizing prompt generation

### ⚙️ Execution Layer
- **Ruflo** — deterministic workflow execution engine
- **agent-orchestrator** — multi-agent coordination and dispatch
- **codebuff** — coding intelligence and code generation

### 🛠️ Tool Layer
- **free-llm-api** — model routing across free and paid providers
- **API registry** — external tool and data source connector
- **gateway** — unified AI endpoint gateway

### 💾 Data Layer
- **cocoindex** — code memory and indexing
- **vector DB memory** — vector embedding storage and retrieval
- **long-term semantic memory** — persistent knowledge graph

### 🔄 Automation Layer
- **floci** — workflow graph definitions and visual editor
- **Ruflo** — workflow execution runtime
- **Open-AutoGLM** — device control and automation

---

## Architecture Flow

```
User Request
    ↓
Intent Router
    ↓
Spec Engine (plan)
    ↓
Agent Orchestrator
    ↓
Workflow Engine (Ruflo)
    ↓
Tool Layer (APIs / LLMs)
    ↓
Execution Layer
    ↓
Memory Update
    ↓
Response
```

---

## Package Structure

```
/packages/
  workflow-engine/        # Ruflo — deterministic workflow execution
  execution-pipeline/     # Task pipelines and execution chains
  task-orchestrator/      # Multi-step automation orchestration
  api-registry/           # External API provider registry
  tool-router/            # Tool selection and routing
  external-api-client/    # Dynamic API client with fallback
```

---

## Capabilities

### Intelligence
- Plan full software systems from natural language
- Break complex tasks into executable workflows
- Self-optimize prompts based on results

### Execution
- Run multi-step deterministic workflows
- Call external APIs dynamically
- Execute tools with automatic retry
- Handle failure with configurable retry policies

### Real-world awareness
- Live data access via external APIs
- Real-time decision making
- Multi-source intelligence gathering

### Autonomy
- Agent collaboration and handoff
- Workflow chaining and composition
- Self-correction loops and learning
