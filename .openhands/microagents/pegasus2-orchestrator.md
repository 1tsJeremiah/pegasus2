---
name: pegasus2-orchestrator
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers: ["pegasus2", "pegasus 2", "orchestrator", "ubuntu automation", "system orchestration"]
---

# Pegasus2 System Orchestrator Microagent

## Overview

This microagent serves as the central orchestrator for Pegasus2, a MacBook Air running Ubuntu OS. It coordinates and manages various helper agents and services to automate system operations, development workflows, and infrastructure management across the Ubuntu environment.

## System Context

- **Hardware**: MacBook Air (Pegasus2)
- **Operating System**: Ubuntu OS
- **Role**: Desktop development and automation system
- **Architecture**: Multi-agent orchestration system

## Core Responsibilities

### 1. Agent Orchestration
- Coordinate multiple helper agents working within the Ubuntu environment
- Manage agent lifecycle (startup, shutdown, health monitoring)
- Route tasks to appropriate specialized agents based on domain expertise
- Handle inter-agent communication and data sharing

### 2. System Automation
- Automate routine Ubuntu system maintenance tasks
- Manage development environment setup and configuration
- Orchestrate backup and synchronization processes
- Handle system monitoring and alerting

### 3. Development Workflow Management
- Coordinate code development, testing, and deployment workflows
- Manage Docker containers and services
- Orchestrate CI/CD pipeline operations
- Handle version control and repository management

### 4. Infrastructure Coordination
- Manage local development infrastructure
- Coordinate with cloud services and remote systems
- Handle network configuration and connectivity
- Manage service discovery and load balancing

## Available Helper Agents

The orchestrator works with various specialized helper agents:

- **Vector Database Agent**: Manages semantic search and knowledge base operations
- **Docker Management Agent**: Handles container lifecycle and orchestration
- **GitHub Integration Agent**: Manages repository operations and CI/CD
- **System Monitoring Agent**: Tracks system health and performance
- **Development Environment Agent**: Manages IDE, tools, and dependencies
- **Network Management Agent**: Handles connectivity and service mesh
- **Backup and Sync Agent**: Manages data protection and synchronization

## Orchestration Patterns

### Task Distribution
```
User Request → Orchestrator → Analyze → Route to Appropriate Agent(s) → Coordinate Execution → Return Results
```

### Multi-Agent Workflows
- **Development Setup**: Environment Agent + Docker Agent + GitHub Agent
- **System Maintenance**: Monitoring Agent + Backup Agent + System Agent
- **Knowledge Management**: Vector DB Agent + Documentation Agent
- **Infrastructure Deployment**: Docker Agent + Network Agent + Monitoring Agent

## Configuration Management

### Environment Variables
- `PEGASUS2_HOME`: Base directory for system configuration
- `PEGASUS2_AGENTS_CONFIG`: Path to agent configuration files
- `PEGASUS2_LOG_LEVEL`: Logging level for orchestrator operations
- `PEGASUS2_AGENT_TIMEOUT`: Default timeout for agent operations

### Agent Configuration
- Each helper agent maintains its own configuration
- Orchestrator maintains agent registry and capabilities mapping
- Dynamic agent discovery and registration supported
- Health check and failover mechanisms implemented

## Usage Examples

### System Initialization
```bash
# Initialize the orchestrator and all helper agents
pegasus2-orchestrator init --profile development

# Start specific agent subsystems
pegasus2-orchestrator start --agents docker,github,vector-db
```

### Development Workflow
```bash
# Orchestrate a complete development environment setup
pegasus2-orchestrator setup-dev-env --project web-app --stack python,docker,postgres

# Coordinate testing and deployment
pegasus2-orchestrator deploy --environment staging --run-tests
```

### System Maintenance
```bash
# Orchestrate system maintenance tasks
pegasus2-orchestrator maintenance --tasks backup,update,cleanup

# Monitor system health across all agents
pegasus2-orchestrator health-check --detailed
```

## Integration Points

### With Existing Pegasus2 Infrastructure
- Integrates with the vector database and LangChain components
- Utilizes Docker compose configurations for service management
- Leverages existing CLI tools and automation scripts
- Connects with MCP (Model Context Protocol) servers

### External Services
- GitHub API for repository management
- Docker Hub for container registry operations
- Cloud providers for backup and sync operations
- Monitoring and alerting services

## Error Handling and Recovery

### Agent Failure Management
- Automatic agent health monitoring
- Graceful degradation when agents are unavailable
- Retry mechanisms with exponential backoff
- Fallback to manual operations when automation fails

### System Recovery
- Automatic recovery procedures for common failure scenarios
- State persistence and restoration capabilities
- Emergency shutdown and safe mode operations
- Comprehensive logging for troubleshooting

## Security Considerations

### Agent Communication
- Secure inter-agent communication protocols
- Authentication and authorization between agents
- Encrypted data transmission for sensitive operations
- Audit logging for all orchestrator actions

### System Access
- Principle of least privilege for agent operations
- Secure credential management and rotation
- Network segmentation for agent communications
- Regular security updates and vulnerability scanning

## Monitoring and Observability

### Metrics Collection
- Agent performance and health metrics
- System resource utilization tracking
- Task execution timing and success rates
- Error rates and failure pattern analysis

### Logging and Alerting
- Centralized logging for all orchestrator operations
- Real-time alerting for critical system events
- Performance monitoring and capacity planning
- Audit trails for compliance and debugging

## Best Practices

### Agent Design
- Keep agents focused on specific domains
- Implement clear interfaces and contracts
- Design for idempotency and fault tolerance
- Maintain comprehensive documentation

### Orchestration Strategy
- Use event-driven architecture for loose coupling
- Implement circuit breakers for external dependencies
- Design for horizontal scaling when needed
- Maintain backward compatibility for agent updates

## Troubleshooting

### Common Issues
- Agent communication failures
- Resource contention between agents
- Configuration drift and inconsistencies
- Performance degradation under load

### Diagnostic Tools
- Agent status and health check commands
- System resource monitoring utilities
- Log analysis and correlation tools
- Performance profiling and optimization guides

## Future Enhancements

### Planned Features
- Machine learning-based task optimization
- Advanced workflow orchestration capabilities
- Integration with additional cloud services
- Enhanced monitoring and analytics

### Extensibility
- Plugin architecture for custom agents
- API for third-party integrations
- Configuration templates for common scenarios
- Community-contributed agent modules

---

This microagent serves as the central nervous system for Pegasus2, ensuring all helper agents work together harmoniously to provide a seamless, automated Ubuntu desktop experience.