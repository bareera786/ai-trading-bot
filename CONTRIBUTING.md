# Contributing Guide

## 🏗️ Architecture Overview

This AI trading bot follows a modular architecture designed for reliability and scalability:

```
├── app/                    # Flask web application
│   ├── routes/            # API endpoints (REST + WebSocket)
│   ├── models/            # Database models (SQLAlchemy)
│   ├── services/          # Business logic layer
│   ├── tasks/             # Background job processing
│   └── templates/         # Jinja2 HTML templates
├── ai_ml_auto_bot_final.py # Main trading engine
├── configs/               # Configuration files
├── database_layer/        # Database abstraction
├── robot_module/          # Trading strategy modules
└── tests/                 # Test suite
```

### Key Design Principles
- **Separation of Concerns**: Web UI, trading logic, and data persistence are decoupled
- **Event-Driven**: Real-time updates via SocketIO
- **Fault-Tolerant**: Comprehensive error handling and recovery
- **Observable**: Structured logging and health monitoring
- **Testable**: Modular design enables comprehensive testing

## 🚀 Development Workflow

### 1. Fork and Clone
```bash
git clone https://github.com/yourusername/ai-trading-bot.git
cd ai-trading-bot
git checkout -b feature/your-feature-name
```

### 2. Set Up Development Environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### 3. Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_trading_engine.py
```

### 4. Code Quality Checks
```bash
# Lint code
ruff check .

# Format code
ruff format .

# Type checking
mypy app/
```

### 5. Database Migrations
```bash
# Create migration
flask db migrate -m "Add new feature"

# Apply migration
flask db upgrade
```

## 📝 Pull Request Process

### PR Requirements
- [ ] Tests pass (`pytest`)
- [ ] Code linted (`ruff check .`)
- [ ] Type checked (`mypy`)
- [ ] Documentation updated
- [ ] Migration scripts included (if schema changes)

### PR Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Migration scripts tested
- [ ] No breaking changes
```

## 🧪 Testing Strategy

### Unit Tests
- Test individual functions and classes
- Mock external dependencies (Binance API, database)
- Focus on business logic validation

### Integration Tests
- Test API endpoints
- Test database operations
- Test background job processing

### End-to-End Tests
- Full trading cycle simulation
- WebSocket real-time updates
- Dashboard functionality

## 🔧 Code Style Guidelines

### Python Standards
- **PEP 8** compliant
- **Type hints** required for all functions
- **Docstrings** for all public functions
- **Descriptive variable names**

### Commit Messages
```
feat: add new trading strategy
fix: resolve memory leak in data processing
docs: update API documentation
refactor: simplify signal generation logic
```

### File Organization
- One class per file (when possible)
- Related functions grouped in modules
- Clear import hierarchy

## 🚨 Security Considerations

### API Keys
- Never commit real API keys
- Use environment variables
- Rotate keys regularly

### Data Handling
- Validate all inputs
- Sanitize database queries
- Log sensitive operations securely

### Deployment
- Use HTTPS in production
- Implement rate limiting
- Regular security audits

## 📚 Documentation

### Code Documentation
- Use Google-style docstrings
- Document complex algorithms
- Include usage examples

### API Documentation
- OpenAPI/Swagger specs
- Endpoint descriptions
- Request/response examples

## 🐛 Debugging

### Logging
- Use structured JSON logging
- Include correlation IDs
- Log at appropriate levels

### Health Checks
- Monitor `/health` endpoint
- Check background worker status
- Validate database connectivity

### Common Issues
- **TA-Lib installation**: Use pandas-ta fallback
- **Database connection**: Check PostgreSQL status
- **Memory usage**: Monitor background tasks

## 🎯 Feature Development

### Adding New Strategies
1. Create strategy class in `robot_module/`
2. Add configuration in `configs/`
3. Update dashboard UI
4. Add tests

### Adding API Endpoints
1. Create route in `app/routes/`
2. Add business logic in `app/services/`
3. Update OpenAPI spec
4. Add tests

### Database Changes
1. Update models in `app/models.py`
2. Create migration script
3. Update queries in services
4. Test migration

## 📞 Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Discord**: Real-time chat
- **Documentation**: `/docs` directory

Thank you for contributing! 🚀
