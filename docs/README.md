# Unified AI System

Advanced pattern-based exploration and integration system that coordinates multiple local LLM agents.

## Components

### Core LLMs

- **Ollama** (port 11434)
  - Models: codellama, deepseek-coder, mistral, neural-chat
  - Specialties: technical implementation, code analysis
  - Status: ✅ Working

- **LM Studio** (port 1234)
  - Models: Multiple specialized models including deepthink-reasoning
  - Specialties: creative exploration, advanced analysis
  - Status: ✅ Working

### Tools

- **TGPT**
  - Purpose: Shell operations & system automation
  - Mode: Interactive shell with auto-execution
  - Usage: `tgpt -s "command" -y`

- **Open Interpreter**
  - Purpose: Code execution & analysis
  - Mode: Local with Ollama backend
  - Usage: `interpreter --local`

### Integration

- **AutoGPT**
  - Location: `external/AutoGPT`
  - Version: Forge (latest)
  - Integration: Works with local LLMs

## Quick Start

1. Start core services:

```bash
# Start Ollama (if not running)
ollama serve

# Start LM Studio
open /Applications/LM\ Studio.app

# Start TGPT shell
tgpt -s "test system" -y

# Start Interpreter
interpreter --local  # Select Ollama when prompted
```

2. Verify services:

```bash
# Check Ollama
curl localhost:11434/api/version

# Check LM Studio
curl localhost:1234/v1/models

# Test TGPT
tgpt -s "echo hello" -y

# Test Interpreter
interpreter --local
```

## Architecture

The system uses a quantum-inspired routing system to coordinate between agents:

1. Task Distribution
   - Ollama: Code & technical tasks
   - LM Studio: Creative & exploration
   - TGPT: Shell & automation
   - Interpreter: Code execution

2. State Management
   - Parallel execution
   - Coherent state tracking
   - Pattern emergence detection

3. Integration Points
   - Shared memory space
   - Cross-agent communication
   - Pattern synthesis

## Development

Current staging version includes:

- Working LLM endpoints
- Tool integration
- State management
- Pattern detection

## Notes

1. System Requirements
   - Darwin/macOS
   - Python 3.13+
   - Node.js 18+

2. Port Usage
   - 11434: Ollama
   - 1234: LM Studio
   - 4891: TGPT
   - 8080: Open Interpreter

3. Known Issues
   - TGPT needs command with -s flag
   - Interpreter requires manual Ollama selection
