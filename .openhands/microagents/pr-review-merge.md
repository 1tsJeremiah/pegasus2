---
name: pr-review-merge
type: knowledge
version: 1.0.0
agent: CodeActAgent
triggers: ["pr review", "pull request review", "merge pr", "auto merge", "pr automation", "code review", "review and merge"]
---

# PR Review and Merge Automation Microagent

## Overview

This microagent automates the process of reviewing and merging pull requests across repositories. It provides intelligent code review capabilities, automated testing validation, and safe merge operations with comprehensive safety checks and rollback mechanisms.

## Core Capabilities

### 1. Automated Code Review
- **Static Code Analysis**: Performs automated code quality checks
- **Security Scanning**: Identifies potential security vulnerabilities
- **Style Compliance**: Validates code formatting and style guidelines
- **Documentation Review**: Ensures proper documentation coverage
- **Test Coverage Analysis**: Verifies adequate test coverage for changes

### 2. Intelligent PR Assessment
- **Change Impact Analysis**: Evaluates the scope and risk of changes
- **Dependency Validation**: Checks for breaking changes in dependencies
- **Performance Impact**: Assesses potential performance implications
- **Compatibility Checks**: Validates backward compatibility
- **Breaking Change Detection**: Identifies potentially breaking modifications

### 3. Automated Testing Integration
- **CI/CD Pipeline Validation**: Ensures all automated tests pass
- **Integration Test Execution**: Runs comprehensive integration tests
- **Regression Testing**: Validates against known regression scenarios
- **Performance Benchmarking**: Compares performance metrics
- **Security Test Validation**: Executes security-focused test suites

### 4. Safe Merge Operations
- **Pre-merge Validation**: Comprehensive checks before merging
- **Conflict Resolution**: Automated handling of simple merge conflicts
- **Rollback Capabilities**: Quick rollback mechanisms for failed merges
- **Branch Protection**: Respects branch protection rules and policies
- **Merge Strategy Selection**: Chooses appropriate merge strategy (merge, squash, rebase)

## Configuration Options

### Review Criteria
```yaml
review_criteria:
  code_quality:
    min_score: 8.0
    check_complexity: true
    check_duplication: true
  
  security:
    vulnerability_scan: true
    dependency_check: true
    secrets_detection: true
  
  testing:
    min_coverage: 80
    require_tests: true
    integration_tests: true
  
  documentation:
    require_docs: true
    api_documentation: true
    changelog_update: true
```

### Merge Policies
```yaml
merge_policies:
  auto_merge_conditions:
    - all_checks_pass: true
    - approvals_required: 1
    - no_conflicts: true
    - branch_up_to_date: true
  
  merge_strategies:
    default: "merge"
    feature_branches: "squash"
    hotfixes: "merge"
    documentation: "squash"
  
  protection_rules:
    respect_branch_protection: true
    require_status_checks: true
    dismiss_stale_reviews: false
```

## Usage Examples

### Basic PR Review
```bash
# Review a specific pull request
pr-review-agent review --repo owner/repo --pr 123

# Review with custom criteria
pr-review-agent review --repo owner/repo --pr 123 --strict-mode

# Review multiple PRs
pr-review-agent review --repo owner/repo --prs 123,124,125
```

### Automated Merge Operations
```bash
# Auto-merge if all criteria are met
pr-review-agent merge --repo owner/repo --pr 123 --auto

# Merge with specific strategy
pr-review-agent merge --repo owner/repo --pr 123 --strategy squash

# Conditional merge based on labels
pr-review-agent merge --repo owner/repo --label "ready-to-merge"
```

### Batch Operations
```bash
# Review all open PRs in a repository
pr-review-agent batch-review --repo owner/repo

# Auto-merge all approved PRs
pr-review-agent batch-merge --repo owner/repo --approved-only

# Process PRs with specific labels
pr-review-agent process --repo owner/repo --labels "auto-merge,reviewed"
```

## Review Process Workflow

### 1. Initial Assessment
```
PR Opened/Updated → Fetch Changes → Analyze Diff → Risk Assessment → Generate Review Plan
```

### 2. Automated Checks
```
Code Quality → Security Scan → Test Validation → Documentation Check → Compliance Verification
```

### 3. Review Generation
```
Compile Results → Generate Comments → Assign Scores → Create Review Summary → Post Feedback
```

### 4. Merge Decision
```
Evaluate Criteria → Check Policies → Validate Approvals → Execute Merge → Post-merge Validation
```

## Integration Capabilities

### GitHub Integration
- **GitHub API**: Full integration with GitHub's REST and GraphQL APIs
- **GitHub Actions**: Seamless integration with CI/CD workflows
- **Status Checks**: Creates and updates commit status checks
- **Review Comments**: Posts detailed inline and general comments
- **Labels Management**: Automatically applies and manages PR labels

### GitLab Integration
- **GitLab API**: Complete integration with GitLab's API
- **Merge Request Automation**: Handles GitLab merge requests
- **Pipeline Integration**: Integrates with GitLab CI/CD pipelines
- **Approval Rules**: Respects GitLab approval workflows

### Bitbucket Integration
- **Bitbucket API**: Integration with Bitbucket Cloud and Server
- **Pull Request Automation**: Manages Bitbucket pull requests
- **Build Status**: Integrates with Bitbucket Pipelines

### External Tools Integration
- **SonarQube**: Code quality and security analysis
- **CodeClimate**: Automated code review and quality metrics
- **Snyk**: Security vulnerability scanning
- **Codecov**: Test coverage analysis and reporting

## Safety Mechanisms

### Pre-merge Validation
- **Comprehensive Testing**: Ensures all tests pass before merge
- **Conflict Detection**: Identifies and resolves merge conflicts
- **Branch Freshness**: Validates branch is up-to-date with target
- **Review Requirements**: Enforces required approvals and reviews

### Rollback Capabilities
- **Automatic Rollback**: Rolls back failed merges automatically
- **State Preservation**: Maintains pre-merge state for recovery
- **Notification System**: Alerts stakeholders of rollback events
- **Audit Trail**: Maintains detailed logs of all operations

### Risk Mitigation
- **Staging Deployment**: Tests changes in staging environment
- **Canary Releases**: Gradual rollout for high-risk changes
- **Feature Flags**: Uses feature toggles for safe deployments
- **Monitoring Integration**: Monitors post-merge metrics and alerts

## Advanced Features

### AI-Powered Review
- **Code Pattern Recognition**: Identifies common code patterns and anti-patterns
- **Contextual Analysis**: Understands code context and business logic
- **Learning Capabilities**: Improves review quality over time
- **Custom Rule Engine**: Supports custom review rules and policies

### Multi-Repository Management
- **Cross-Repository Dependencies**: Manages dependencies across repos
- **Coordinated Releases**: Orchestrates releases across multiple repositories
- **Shared Configuration**: Maintains consistent policies across projects
- **Bulk Operations**: Performs operations across multiple repositories

### Reporting and Analytics
- **Review Metrics**: Tracks review quality and efficiency metrics
- **Merge Statistics**: Provides insights into merge patterns and success rates
- **Team Performance**: Analyzes team productivity and code quality trends
- **Custom Dashboards**: Creates customizable reporting dashboards

## Configuration Examples

### Basic Configuration
```yaml
# .openhands/pr-review-config.yml
repositories:
  - name: "owner/repo"
    auto_merge: true
    review_required: true
    min_approvals: 1
    
review_settings:
  code_quality_threshold: 7.5
  security_scan_required: true
  test_coverage_min: 75
  
merge_settings:
  default_strategy: "merge"
  delete_branch_after_merge: true
  update_branch_before_merge: true
```

### Advanced Configuration
```yaml
# .openhands/pr-review-advanced.yml
repositories:
  - name: "owner/critical-repo"
    auto_merge: false
    review_required: true
    min_approvals: 2
    required_reviewers: ["senior-dev", "tech-lead"]
    
    rules:
      - condition: "files_changed < 10 AND tests_added"
        action: "auto_approve"
      - condition: "security_issues > 0"
        action: "block_merge"
      - condition: "breaking_changes"
        action: "require_manual_review"
    
    integrations:
      sonarqube:
        enabled: true
        quality_gate: "strict"
      snyk:
        enabled: true
        severity_threshold: "medium"
```

## API Integration Examples

### GitHub API Usage
```python
# Example: Automated PR review using GitHub API
async def review_pull_request(repo, pr_number):
    # Fetch PR details
    pr = await github_client.get_pull_request(repo, pr_number)
    
    # Perform automated checks
    code_quality = await analyze_code_quality(pr.diff)
    security_issues = await scan_security_vulnerabilities(pr.files)
    test_coverage = await calculate_test_coverage(pr.files)
    
    # Generate review
    review_comments = generate_review_comments(
        code_quality, security_issues, test_coverage
    )
    
    # Post review
    await github_client.create_review(
        repo, pr_number, review_comments, "APPROVE" if all_checks_pass else "REQUEST_CHANGES"
    )
    
    # Auto-merge if criteria met
    if should_auto_merge(pr, code_quality, security_issues):
        await github_client.merge_pull_request(repo, pr_number, "merge")
```

### GitLab API Usage
```python
# Example: GitLab merge request automation
async def process_merge_request(project_id, mr_iid):
    # Get merge request details
    mr = await gitlab_client.get_merge_request(project_id, mr_iid)
    
    # Check pipeline status
    pipeline_status = await gitlab_client.get_pipeline_status(
        project_id, mr.source_branch
    )
    
    # Validate merge conditions
    if pipeline_status == "success" and mr.approvals_count >= required_approvals:
        # Execute merge
        await gitlab_client.merge_request(
            project_id, mr_iid, merge_when_pipeline_succeeds=True
        )
```

## Monitoring and Alerting

### Metrics Collection
- **Review Processing Time**: Time taken for automated reviews
- **Merge Success Rate**: Percentage of successful merges
- **False Positive Rate**: Accuracy of automated assessments
- **Developer Satisfaction**: Feedback on review quality

### Alert Conditions
- **Failed Merges**: Immediate alerts for merge failures
- **Security Issues**: High-priority alerts for security vulnerabilities
- **Quality Degradation**: Alerts when code quality drops below threshold
- **Pipeline Failures**: Notifications for CI/CD pipeline failures

## Best Practices

### Review Quality
- **Consistent Standards**: Maintain consistent review criteria across projects
- **Contextual Feedback**: Provide specific, actionable feedback
- **Learning Integration**: Continuously improve review algorithms
- **Human Oversight**: Maintain human review for critical changes

### Merge Safety
- **Gradual Rollout**: Implement changes gradually in production
- **Monitoring Integration**: Monitor post-merge metrics closely
- **Quick Rollback**: Maintain ability to quickly rollback changes
- **Communication**: Keep stakeholders informed of automated actions

### Team Integration
- **Training**: Provide training on automated review processes
- **Feedback Loop**: Collect and act on team feedback
- **Customization**: Allow teams to customize review criteria
- **Transparency**: Maintain visibility into automated decisions

## Troubleshooting

### Common Issues
- **API Rate Limits**: Handle GitHub/GitLab API rate limiting
- **Merge Conflicts**: Automated conflict resolution strategies
- **Test Failures**: Handling flaky tests and false negatives
- **Permission Issues**: Managing repository access and permissions

### Debugging Tools
- **Detailed Logging**: Comprehensive logs for all operations
- **Dry Run Mode**: Test configurations without actual merges
- **Manual Override**: Allow manual intervention when needed
- **Audit Trail**: Complete history of all automated actions

---

This microagent provides comprehensive PR review and merge automation capabilities while maintaining safety, quality, and team collaboration standards. It can be customized for different repository types, team workflows, and organizational policies.