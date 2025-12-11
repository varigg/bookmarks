# Contributing to Bookmarks

Thank you for your interest in contributing to this project! This guide will help you get started.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue using the bug report template
3. Include detailed steps to reproduce, expected behavior, and actual behavior
4. Add screenshots if applicable

### Suggesting Enhancements

1. Check if the enhancement has already been suggested
2. Create a new issue using the feature request template
3. Clearly describe the feature and its benefits
4. Consider if it aligns with the project's goals (self-hosted, personal use)

### Pull Requests

1. **Fork the repository**

   ```bash
   git clone https://github.com/yourusername/bookmarks.git
   cd bookmarks
   ```

2. **Create a feature branch**

   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**

   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests**

   ```bash
   uv run pytest
   uv run pytest --cov=bookmarks  # With coverage
   ```

5. **Run linter**

   ```bash
   uv run ruff check .
   uv run ruff format .
   ```

6. **Commit your changes**

   ```bash
   git commit -m 'Add amazing feature'
   ```

   Use conventional commit messages:

   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `refactor:` for code refactoring
   - `test:` for test changes
   - `chore:` for maintenance tasks

7. **Push to your fork**

   ```bash
   git push origin feature/amazing-feature
   ```

8. **Open a Pull Request**
   - Fill in the PR template
   - Link any related issues
   - Wait for review

## Development Setup

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/bookmarks.git
cd bookmarks

# Install dependencies
uv sync

# Run the application
uv run flask --app wsgi run --debug
```

### Project Structure

```
bookmarks/
├── bookmarks/          # Main application package
│   ├── core/          # Domain models and exceptions
│   ├── data/          # Data access layer
│   ├── web/           # Flask routes and views
│   └── services/      # Business logic (LLM, bookmarks)
├── tools/             # CLI utilities
├── tests/             # Test suite
└── docs/              # Documentation
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for public functions and classes
- Keep functions small and focused
- Use meaningful variable names

This project uses **Ruff** for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .
```

## Testing

- Write tests for new features
- Maintain or improve code coverage
- Run the full test suite before submitting PR

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=bookmarks --cov-report=html

# Run specific test file
uv run pytest tests/test_app.py -v
```

## Documentation

- Update README.md if adding user-facing features
- Update relevant documentation in `docs/` folder
- Add docstrings to new functions and classes
- Update CONFIGURATION.md if adding new environment variables

## Areas for Contribution

### High Priority

- Additional LLM provider implementations (OpenAI, Anthropic)
- Automated tag suggestions based on content
- Improved error handling and user feedback
- Browser extension improvements
- Mobile app (React Native or similar)

### Medium Priority

- Export/import functionality (various formats)
- Bookmark collections/folders
- Full-text search
- Duplicate detection improvements
- Performance optimizations

### Documentation

- Video tutorials
- More detailed setup guides
- Troubleshooting guides
- Example configurations

## Questions?

Feel free to open an issue for questions or reach out to the maintainers.

## Code of Conduct

Please note that this project has a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to abide by its terms.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
