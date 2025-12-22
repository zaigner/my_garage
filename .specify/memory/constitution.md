# My Garage - Project Constitution

## Project Vision

My Garage is an automotive asset management platform that empowers car enthusiasts to track, manage, and understand the financial value of their vehicles. We believe that every car is an investment, and owners deserve professional-grade tools to manage their automotive assets.

## Core Principles

### 1. User-Centric Design
- **Principle**: The user experience comes first, always.
- **Practice**: Every feature must have a clear user benefit and intuitive interface.
- **Example**: Admin interface provides immediate CRUD functionality without custom development needed.

### 2. Data Accuracy & Integrity
- **Principle**: Financial data must be precise and reliable.
- **Practice**: Use `Decimal` for all monetary values, never floats. Use database-level constraints and validation.
- **Example**: All financial calculations use `Decimal` type with proper rounding and precision.

### 3. Separation of Concerns
- **Principle**: Code organization follows clear architectural patterns.
- **Practice**: Service layer pattern with distinct responsibilities (models, selectors, services, views).
- **Example**: `api/selectors.py` handles reads, `api/services.py` handles writes and business logic.

### 4. Testability & Maintainability
- **Principle**: Code should be easy to test and maintain.
- **Practice**: Pure functions, dependency injection, clear interfaces. Each layer independently testable.
- **Example**: Selectors return data without side effects; services use `@transaction.atomic` for testable transactions.

### 5. Progressive Enhancement
- **Principle**: Build solid foundations before adding complexity.
- **Practice**: Start with working Django app, then add AI/ML features incrementally.
- **Example**: Admin interface works now; FastAPI microservices added later.

### 6. Security by Default
- **Principle**: Security is not optional.
- **Practice**: Follow Django security best practices, validate input, use CSRF tokens, secure sessions.
- **Example**: Production settings enforce HTTPS, HSTS, secure cookies.

### 7. Performance Awareness
- **Principle**: Optimize for the common case, but don't prematurely optimize.
- **Practice**: Use database aggregations, select_related/prefetch_related, async tasks for heavy operations.
- **Example**: Financial calculations done at database level with `Coalesce` and `Sum`.

## Technical Architecture Guidelines

### Django Project Structure
- **Configuration** in `config/` separate from application code
- **Applications** in `django_apps/` following single responsibility
- **Settings** split by environment (base, local, production, test)
- **Static/Media** files properly organized and served

### Service Layer Pattern (django-kedro inspired)
- **Models** (`models.py`): Pure data definitions, no business logic
- **Selectors** (`api/selectors.py`): Read-only database queries and aggregations
- **Services** (`api/services.py`): Business logic, mutations, external API calls
- **Views** (`views.py`): HTTP orchestration, thin layer calling selectors/services
- **Tasks** (`tasks.py`): Background jobs via Celery
- **Forms** (`forms.py`): User input validation and rendering
- **Admin** (`admin.py`): Comprehensive admin interface configuration

### Naming Conventions
- **Selectors**: `{model}_get_{description}`, `{model}_list_{description}`
- **Services**: `{model}_{action}_{description}` where action is create/update/delete/process
- **Tasks**: `task_{action}_{description}`
- **Views**: descriptive function/class names following Django conventions

### Database Design
- **Financial Fields**: Use `DecimalField` with `max_digits=12, decimal_places=2`
- **Relationships**: Clear ForeignKey with `on_delete` behavior defined
- **Validation**: Field-level validators where possible
- **Timestamps**: `auto_now_add` for creation, `auto_now` for updates
- **Choices**: Use TextChoices enums for readability

### Error Handling
- **Custom Exceptions**: Define domain-specific exceptions in services
- **Transaction Safety**: Use `@transaction.atomic` for multi-record operations
- **Graceful Degradation**: Handle external API failures gracefully
- **User Feedback**: Clear, actionable error messages in UI

## Development Workflow

### Code Organization
1. **Models First**: Define data schema before logic
2. **Selectors Next**: Create read operations for views
3. **Services Then**: Add business logic and mutations
4. **Views Last**: Wire up HTTP layer calling selectors/services
5. **Tests Throughout**: Write tests as you go, not after

### Testing Strategy
- **Unit Tests**: Test selectors and services in isolation
- **Integration Tests**: Test views with mocked external services
- **Transaction Tests**: Verify atomic operations rollback correctly
- **Mock External APIs**: Don't call real FastAPI/MCP in tests

### Git Workflow
- **Commit Often**: Small, focused commits with clear messages
- **Descriptive Messages**: Explain what and why, not just what
- **Phase Organization**: Group related changes into phases
- **Documentation**: Update relevant docs with code changes

## Technology Decisions

### Why Django?
- **Mature Ecosystem**: Proven framework with extensive library support
- **Admin Interface**: Auto-generated CRUD interface saves development time
- **ORM**: Powerful database abstraction with migration support
- **Security**: Built-in protection against common vulnerabilities
- **Community**: Large community, extensive documentation

### Why Service Layer Pattern?
- **Testability**: Pure functions easier to test than fat models
- **Reusability**: Services can be called from views, tasks, management commands
- **Clarity**: Clear separation between reads (selectors) and writes (services)
- **Maintainability**: Easier to understand and modify business logic

### Why Separate FastAPI Service?
- **Performance**: Offload compute-intensive AI/OCR tasks
- **Scalability**: Can scale FastAPI independently from Django
- **Technology Choice**: Use best tool for each job (FastAPI for async, Django for CRUD)
- **Isolation**: AI service failures don't crash main application

### Why Celery?
- **Background Processing**: Long-running tasks don't block HTTP requests
- **Scheduling**: Celery Beat for periodic market value updates
- **Reliability**: Task retries and error handling built-in
- **Monitoring**: Flower and other tools for task monitoring

## Quality Standards

### Code Quality
- **Type Hints**: All function signatures should have type hints
- **Docstrings**: All public functions/classes have docstrings
- **Comments**: Explain **why**, not **what** (code shows what)
- **Formatting**: Follow PEP 8, use consistent style

### Testing Coverage
- **Target**: Aim for 80%+ coverage on business logic
- **Priority**: Services and selectors must be well-tested
- **Edge Cases**: Test error conditions, not just happy paths
- **Fixtures**: Use factories for test data generation

### Documentation
- **README**: Quick start guide for new developers
- **claude.md**: Comprehensive project guide for AI assistance
- **design.md**: Feature specifications and architecture decisions
- **Inline Docs**: Complex algorithms deserve explanation comments

### Performance
- **Database**: N+1 queries are bugs, use select_related/prefetch_related
- **Caching**: Cache expensive calculations, invalidate appropriately
- **Async**: Use Celery for operations >1 second
- **Monitoring**: Log slow queries and long-running operations

## Security Guidelines

### Authentication & Authorization
- **Django Auth**: Use Django's built-in authentication system
- **Per-Object Permissions**: Users can only access their own vehicles
- **Admin Access**: Strict controls on who can access admin interface

### Data Protection
- **Secrets Management**: Never commit secrets to git
- **Environment Variables**: Use `.env` for sensitive configuration
- **HTTPS Only**: Enforce HTTPS in production (SECURE_SSL_REDIRECT)
- **CSRF Protection**: Use Django's CSRF middleware

### Input Validation
- **Form Validation**: Validate all user input via Django forms
- **API Validation**: Use DRF serializers for API input
- **File Uploads**: Validate file types and sizes
- **SQL Injection**: Use ORM, never raw SQL with user input

### API Security
- **Authentication Required**: Require login for all non-public endpoints
- **Rate Limiting**: Implement rate limiting on API endpoints
- **CORS**: Restrict CORS to known origins in production

## Future-Proofing

### Extensibility
- **Plugin Architecture**: Service layer makes adding features easy
- **API First**: Design APIs even for internal use
- **Microservices Ready**: FastAPI service demonstrates multi-service architecture
- **Data Model**: JSONField allows schema evolution without migrations

### Scalability
- **Database**: PostgreSQL for production (supports millions of records)
- **Caching**: Redis already integrated for Celery, can add caching
- **Load Balancing**: WSGI/ASGI apps can run behind load balancer
- **CDN**: Static/media files can move to CDN as needed

### Maintainability
- **Clear Patterns**: Consistent code patterns reduce cognitive load
- **Documentation**: Keep docs up-to-date with code
- **Testing**: Comprehensive tests enable confident refactoring
- **Monitoring**: Log important events for debugging

## Non-Goals

### What We Don't Do
- **Multi-tenancy**: Single-user or family use, not SaaS
- **Real-time Collaboration**: No WebSocket for real-time editing
- **Mobile-First**: Desktop web UI first, mobile later
- **Blockchain**: No cryptocurrency or NFT integration
- **Social Network**: No friend feeds or social features (yet)

## Decision Framework

When making technical decisions, ask:

1. **Does it serve the user?** Will users benefit from this?
2. **Is it maintainable?** Can we understand and modify this in 6 months?
3. **Is it testable?** Can we write automated tests for this?
4. **Is it secure?** Does this introduce security risks?
5. **Is it scalable?** Will this work with 10x the data?
6. **Is it simple?** Is this the simplest solution that works?

If the answer to any is "no", reconsider the approach.

---

**Last Updated**: 2025-12-21
**Version**: 1.0
**Status**: Living Document (update as project evolves)
