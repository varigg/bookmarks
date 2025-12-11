# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

Please report security vulnerabilities by opening a private security advisory on GitHub or contacting the maintainer directly.

**Do not** open public issues for security vulnerabilities.

## Security Best Practices

### For Self-Hosting

1. **API Keys**: Always use environment variables, never commit to git

   ```bash
   export PERPLEXITY_API_KEY="your-key-here"
   ```

2. **Network Security**:

   - Run behind a reverse proxy (nginx) with HTTPS in production
   - Consider firewall rules to restrict access to your local network
   - Use strong `BOOKMARKS_SECRET_KEY` for Flask sessions

3. **Data Protection**:

   - Regular backups (automatic backup feature enabled by default)
   - Keep `bookmarks.js` secure with appropriate file permissions

4. **Dependencies**:
   - Keep dependencies updated: `uv sync --upgrade`
   - Monitor for security advisories

### Known Considerations

- This application is designed for personal/home network use
- Not recommended for public internet exposure without additional hardening
- CSRF protection is currently disabled for REST API compatibility

## Disclosure Policy

We will acknowledge receipt of vulnerability reports within 48 hours and aim to provide a fix within 7 days for critical issues.
