# .specify - Spec-Driven Development

This directory contains specifications and project governance documents following the [spec-kit](https://github.com/github/spec-kit) methodology for spec-driven development.

## Directory Structure

```
.specify/
├── memory/                      # Project memory and principles
│   └── constitution.md         # Project constitution and core principles
├── specs/                       # Feature specifications
│   └── 001-my-garage-platform/ # Main platform specification
│       └── spec.md             # Feature spec with user stories
└── templates/                   # Templates for new specs
    └── spec-template.md        # Template for creating new feature specs
```

## Purpose

The `.specify/` directory serves as the single source of truth for:
- **Project Principles** (constitution.md) - Governing principles and technical decisions
- **Feature Specifications** (specs/) - What we're building and why
- **Technical Plans** - How we'll implement features
- **Documentation** - Living documents that evolve with the project

## Spec-Driven Development Workflow

1. **Constitution First**: Establish project principles and technical standards
2. **Specification**: Define requirements and user stories
3. **Planning**: Create technical implementation plan
4. **Task Breakdown**: Generate actionable task lists
5. **Implementation**: Build features following the spec

## Files

### constitution.md
The project constitution contains:
- Project vision and core principles
- Technical architecture guidelines
- Coding conventions and naming patterns
- Quality standards and testing requirements
- Security guidelines
- Decision-making framework

**When to Update**: When making foundational technical decisions or changing architectural patterns.

### spec.md
Feature specifications contain:
- Problem statement and user pain points
- User stories with acceptance criteria
- Technical specification (data models, APIs)
- Implementation status and roadmap
- Success metrics and testing strategy
- Risks and mitigations

**When to Update**: When starting new features, after completing major milestones, or when requirements change.

## Creating New Specifications

When adding a new feature:

1. Create a new directory in `specs/` with a number prefix:
   ```bash
   mkdir -p .specify/specs/002-new-feature
   ```

2. Copy the template:
   ```bash
   cp .specify/templates/spec-template.md .specify/specs/002-new-feature/spec.md
   ```

3. Fill in the specification:
   - Problem statement
   - User stories
   - Technical design
   - Implementation plan

4. Reference the constitution:
   - Ensure alignment with project principles
   - Follow established patterns
   - Maintain consistency

## Benefits

### For Development
- **Clear Requirements**: No ambiguity about what to build
- **Architectural Consistency**: All features follow same patterns
- **Easier Onboarding**: New developers understand the "why" behind decisions
- **Better Testing**: Acceptance criteria guide test creation

### For AI Assistance
- **Context**: AI agents understand project structure and conventions
- **Consistency**: AI suggestions align with established patterns
- **Quality**: AI generates code following project standards
- **Documentation**: Specs serve as knowledge base for AI

### For Maintenance
- **Decision Log**: Track why choices were made
- **Change Impact**: Understand dependencies when modifying features
- **Refactoring**: Know what not to break
- **Evolution**: See how project grew over time

## Integration with Development

### Before Writing Code
1. Read `constitution.md` for project principles
2. Read relevant spec for feature requirements
3. Understand acceptance criteria
4. Follow established patterns

### While Writing Code
1. Reference spec for business logic details
2. Use naming conventions from constitution
3. Follow architectural patterns
4. Add tests for acceptance criteria

### After Writing Code
1. Update spec with implementation status
2. Document any deviations from plan
3. Add lessons learned
4. Mark acceptance criteria as complete

## Maintenance

### Review Cadence
- **Constitution**: Review when making architectural changes
- **Specs**: Review after completing major features
- **Templates**: Update as patterns evolve

### Version Control
- All spec files are tracked in git
- Changes are committed with code changes
- Specs evolve alongside implementation

### Living Documents
These are **living documents** that evolve with the project:
- Update specs as requirements clarify
- Refine principles based on experience
- Add lessons learned
- Keep status current

---

**Created**: 2025-12-21
**Last Updated**: 2025-12-21
**Methodology**: [Spec-Kit](https://github.com/github/spec-kit)
