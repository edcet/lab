# Local AI Coordination Rules

## 1. Task Delegation Structure

### Ollama (localhost:11434)

Primary: Code Analysis & Refactoring

```bash
# Rule Structure
ollama run codellama "
<context>
- Current task scope
- File/directory context
- Integration points
</context>

<rules>
1. Analyze before modifying
2. Verify dependencies
3. Check integration points
</rules>

<output_format>
1. Analysis results
2. Proposed changes
3. Verification steps
</output_format>
"
```

### TGPT (Shell Mode)

Primary: Environment & Shell Integration

```bash
# Interactive Mode Rules
tgpt --shell "
<environment>
- Shell: $SHELL
- PWD: $PWD
- Context: $CURRENT_TASK
</environment>

<validation>
1. Check current state
2. Propose changes
3. Verify impact
</validation>

<output>
1. Current status
2. Recommended actions
3. Verification steps
</output>
"
```

### LM Studio (localhost:1234)

Primary: Documentation & Verification

```json
{
  "messages": [{
    "role": "system",
    "content": "
      <documentation_rules>
      1. Maintain context awareness
      2. Track changes in real-time
      3. Verify documentation accuracy
      </documentation_rules>

      <verification_steps>
      1. Pre-change validation
      2. Post-change verification
      3. Integration testing
      </verification_steps>
    "
  }]
}
```

## 2. Integration Protocol

### Communication Channels

1. Direct API Calls

   ```bash
   # Health Check Protocol
   curl localhost:11434/api/health
   curl localhost:1234/v1/health
   curl localhost:4891/health
   ```

2. Shell Integration

   ```bash
   # Standardized Input Format
   {task_type}::{context}::{validation_rules}
   ```

3. Response Handling

   ```bash
   # Output Structure
   status::analysis::recommendations::verification
   ```

## 3. Monitoring Rules

### Active Monitoring

1. Service Health

   ```bash
   # Health Check Interval: 60s
   while true; do
     check_ai_services
     sleep 60
   done
   ```

2. Response Validation

   ```bash
   # Validation Protocol
   validate_response() {
     check_format
     verify_context
     confirm_rules_followed
   }
   ```

3. Error Handling

   ```bash
   # Error Protocol
   handle_error() {
     log_error
     attempt_recovery
     notify_if_critical
   }
   ```

## 4. Task Processing Rules

### Pre-execution

1. Context Gathering
   - Current environment state
   - Task dependencies
   - Integration requirements

2. Validation Checks
   - Resource availability
   - Permission verification
   - Dependency resolution

### Execution

1. Coordinated Processing

   ```bash
   # Task Distribution
   distribute_task() {
     ollama_component
     tgpt_component
     lmstudio_component
   }
   ```

2. Synchronization

   ```bash
   # Sync Protocol
   sync_ai_tools() {
     verify_states
     align_contexts
     confirm_readiness
   }
   ```

### Post-execution

1. Verification
   - Result validation
   - Integration testing
   - Documentation updates

2. Cleanup
   - Resource release
   - State restoration
   - Log compilation

## 5. Documentation Requirements

### Real-time Updates

1. Change Tracking

   ```markdown
   ## Change Log
   - Timestamp
   - Modification
   - Verification
   ```

2. Context Preservation

   ```markdown
   ## Context
   - Previous state
   - Current state
   - Integration points
   ```

### Verification Points

- [ ] Rule compliance
- [ ] Integration status
- [ ] Documentation accuracy
- [ ] Performance metrics

```
