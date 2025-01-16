# NFX Neural Integration

The NFX Neural Integration module provides advanced neural processing capabilities by integrating various neural components with the NFX framework.

## Components

### 1. Neural Manipulation
- `NeuralManipulator`: Handles parallel model manipulation
- `NeuralWarfare`: Aggressive model control and injection
- `AIGatewayController`: Gateway management and routing

### 2. Memory Management
- `NeuralMemoryCore`: Core memory manipulation
- `NeuralMemoryManipulator`: Direct memory access with quantum capabilities
- Memory patterns and transforms

### 3. CLI and Orchestration
- `NeuralCLI`: Command-line interface
- `LocalAIOrchestrator`: Task orchestration
- Event bus and state management

## Usage

### CLI Commands

1. Initialize Neural Components
```bash
nfx neural initialize
```

2. Process Neural Task
```bash
nfx neural process --prompt "Your prompt" --parallel 4 --model ollama
```

3. Check System Status
```bash
nfx neural status
```

4. Cleanup Components
```bash
nfx neural cleanup
```

### Configuration

The neural system uses the following default endpoints:
- Ollama: http://localhost:11434
- TGPT: http://localhost:4891
- LM Studio: http://localhost:1234
- Jan: http://localhost:1337

### Resource Requirements

Default resource requirements per task:
- GPU Memory: 4GB
- CPU Cores: 4
- RAM: 8GB
- Shared Memory: 4GB

## Integration Architecture

```
NFX Framework
├── Core Components
│   ├── ComputeEngine
│   ├── MemoryManager
│   └── ProcessOrchestrator
│
├── Neural Components
│   ├── NeuralManipulator
│   ├── NeuralWarfare
│   └── AIGatewayController
│
├── Memory Components
│   ├── NeuralMemoryCore
│   └── NeuralMemoryManipulator
│
└── CLI Components
    └── NeuralCLI
```

## Advanced Features

1. Parallel Processing
- Multi-threaded execution (16 worker threads)
- Multi-process execution (8 worker processes)
- Parallel model inference

2. Memory Management
- Direct memory manipulation
- Quantum memory capabilities
- Advanced memory patterns

3. Gateway Control
- Multiple model endpoints
- Automatic failover
- Load balancing

4. Neural Warfare
- Aggressive model control
- Pattern injection
- Advanced manipulation

## Error Handling

The system includes comprehensive error handling:
- Component initialization failures
- Task execution errors
- Resource allocation failures
- Gateway communication errors

## Logging

Logging is configured through the standard Python logging module:
```python
logger = logging.getLogger("nfx.neural")
```

## Contributing

When contributing to the neural integration:
1. Follow the existing code structure
2. Add comprehensive error handling
3. Include logging statements
4. Update documentation
5. Add tests for new functionality
