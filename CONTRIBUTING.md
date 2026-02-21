# Contributing to KSERC ARA Backend

Thank you for your interest in contributing to the KSERC Autonomous Regulatory Agent Backend!

## Code Style and Documentation Standards

This project follows strict documentation standards to ensure maintainability and knowledge transfer.

### Documentation Requirements

Every file in this project must follow these rules:

1. **Every line must be commented** (except basic Python operations)
2. **Source attribution** for each function:
   - Mark as `[User Defined]` if you wrote it
   - Mark as `[Library]` if it's from an external library
   - Mark as `[Source]` with reference if adapted from elsewhere
3. **Explain the "Why"** - Don't just say what the code does, explain why it's needed
4. **Library functions** - Always explain why a particular library function is used

### Comment Format

Use these comment markers consistently:

```python
# [Purpose] - What this file/function does
# [Source] - Where the code came from
# [Why] - Why this approach was chosen
# [Library] - When calling a library function
# [User Defined] - For custom functions
# [Comment] - General inline comments
# [Note] - Important information
# [TODO] - Future improvements
# [Example] - Usage examples
```

### Example of Proper Documentation

```python
# [Purpose] Calculates percentage deviation from approved amount
# [Source] User defined using standard financial formula
# [Why] Percentage gives better context than absolute values
def calculate_deviation_percentage(approved: float, actual: float) -> float:
    """
    [Purpose] Converts absolute deviation to percentage
    [Parameters]
    - approved: ARR approved amount
    - actual: Actual expenditure
    
    [Returns]
    - float: Percentage deviation
    
    [Formula] ((Actual - Approved) / Approved) * 100
    """
    # [Comment] Handle division by zero
    if approved == 0:
        # [Library] logging.warning() to track edge cases
        logger.warning("Approved amount is zero")
        return 0.0
    
    # [Comment] Calculate using standard formula
    # [Why] Shows relative impact better than absolute values
    percentage = ((actual - approved) / approved) * 100
    
    # [Library] round() to limit decimal places
    # [Why] Two decimals sufficient for regulatory reporting
    return round(percentage, 2)
```

## Development Workflow

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork
3. Create a virtual environment
4. Install dependencies including dev tools

```bash
git clone https://github.com/YOUR_USERNAME/KSERCnew.git
cd KSERCnew
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Making Changes

1. Create a new branch for your feature/fix
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes following the documentation standards

3. Test your changes
```bash
# Run the test script
python test_api.py

# Manual testing
python src/main.py
# Then test endpoints at http://localhost:8000/docs
```

4. Commit with descriptive messages
```bash
git add .
git commit -m "Add feature: description of what you added"
```

5. Push and create a pull request
```bash
git push origin feature/your-feature-name
```

## Code Architecture

### Project Structure

```
src/
├── main.py           # FastAPI application entry point
├── config.py         # Configuration management
├── models/
│   └── schemas.py    # Pydantic data models
├── services/
│   ├── pdf_ingestion.py  # PDF parsing logic
│   └── analyzer.py       # Analysis and compliance checks
└── utils/
    └── logger.py     # Logging utilities
```

### Design Principles

1. **Separation of Concerns**: Keep API layer separate from business logic
2. **Type Safety**: Use Pydantic models for all data structures
3. **Error Handling**: Comprehensive exception handling at all levels
4. **Logging**: Detailed logging for debugging and audit trails
5. **Documentation**: Every function has purpose, parameters, returns, and examples

## Adding New Features

### Adding a New Endpoint

1. Define Pydantic models in `src/models/schemas.py`
2. Implement business logic in appropriate service file
3. Add endpoint in `src/main.py`
4. Document with comments following standards
5. Add tests in `test_api.py`

Example:
```python
# In src/main.py
@app.post("/new-endpoint/", response_model=NewResponseModel)
async def new_endpoint(data: NewRequestModel):
    """
    [Purpose] Brief description of what this endpoint does
    [Source] User defined endpoint
    [Why] Explain why this endpoint is needed
    """
    # Implementation with full comments
    pass
```

### Adding a New Library

When adding a new library:

1. Add to `requirements.txt` with version and explanation:
```
# [Library] new-library-name - Brief description
# [Source] https://library-url.com
# [Why] Explanation of why this library is needed
# [Usage] Where it will be used in the codebase
new-library-name==1.0.0
```

2. Document its usage in code with `[Library]` markers

### Adding Analysis Features

For new analysis features, add to `src/services/analyzer.py`:

1. Follow the existing function structure
2. Include comprehensive docstrings
3. Explain the regulatory context
4. Add validation and error handling
5. Log key steps for audit trail

## Testing

### Running Tests

```bash
# Run all API tests
python test_api.py

# Start server manually and test interactively
python src/main.py
# Visit http://localhost:8000/docs
```

### Adding Tests

When adding new features, add corresponding tests to `test_api.py`:

```python
def test_your_feature(base_url: str):
    """Test your new feature"""
    # Test implementation
    pass
```

## Common Tasks

### Updating Dependencies

```bash
pip install --upgrade package-name
pip freeze > requirements.txt
# Update the package entry in requirements.txt with explanation
```

### Debugging

1. Set `LOG_LEVEL=DEBUG` in `.env`
2. Check console output with color-coded log levels
3. Review specific function logs with module names
4. Use the detailed error messages from exceptions

### Performance Optimization

When optimizing:
1. Profile with actual KSERC PDFs
2. Document performance implications in comments
3. Maintain backward compatibility
4. Keep the API response time < 3 seconds for typical PDFs

## Regulatory Context

Understanding KSERC's regulatory framework helps contribute effectively:

- **Truing Up**: Comparing approved ARR vs actual expenditure
- **Deviation Analysis**: Identifying significant over/under spending
- **Compliance Checks**: Ensuring mathematical accuracy and regulatory adherence
- **Financial Year**: Indian FY format (YYYY-YY, e.g., 2023-24)

## Questions?

For questions about:
- Code architecture: Check inline comments and docstrings
- Regulatory context: Review KSERC orders in the docs
- Contribution process: Open an issue on GitHub
- Direct contact: [@prak05](https://github.com/prak05)

## Code Review Checklist

Before submitting a PR, ensure:

- [ ] All new code has comprehensive comments
- [ ] Function purposes and sources are documented
- [ ] Library functions are explained with "Why"
- [ ] Type hints are used for all functions
- [ ] Error handling is comprehensive
- [ ] Logging is added for key operations
- [ ] Tests are added for new features
- [ ] README is updated if needed
- [ ] No sensitive data in code or commits

## Recognition

Contributors will be acknowledged in:
- GitHub contributors list
- Future release notes
- Project documentation

Thank you for helping make KSERC's regulatory processes more efficient!
