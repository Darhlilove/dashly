# Security Documentation

## Overview

This document outlines the security measures implemented in the Dashly backend API to protect against common vulnerabilities and ensure safe operation.

## Security Features Implemented

### 1. Authentication & Authorization

- **API Key Authentication**: All endpoints require valid API key authentication
- **Configurable Authentication**: Can be disabled for development (REQUIRE_AUTH=false)
- **Secure Key Requirements**: API keys must be at least 16 characters long
- **No Default Keys**: Prevents use of default/demo keys in production

### 2. SQL Injection Prevention

- **Comprehensive SQL Validator**: Advanced validation beyond simple keyword blacklisting
- **Parameterized Queries**: All database operations use parameterized queries
- **Query Structure Validation**: Ensures only SELECT statements are allowed
- **Function Whitelisting**: Only safe SQL functions are permitted
- **Comment Removal**: SQL comments are stripped to prevent hidden malicious code

### 3. Path Traversal Protection

- **Path Validation**: All file paths are validated to prevent directory traversal
- **Project Boundary Enforcement**: Files must be within project directory
- **Secure Path Resolution**: Uses Path.resolve() for safe path handling

### 4. Input Validation & Sanitization

- **File Upload Validation**: CSV files are validated for format, size, and content
- **Data Sanitization**: Sensitive data is redacted in API responses
- **Request Size Limits**: Prevents resource exhaustion attacks
- **Query Length Limits**: Reasonable limits on query complexity

### 5. Security Headers

- **Content Security Policy (CSP)**: Prevents XSS attacks
- **X-Frame-Options**: Prevents clickjacking
- **X-Content-Type-Options**: Prevents MIME type sniffing
- **Strict Transport Security**: Enforces HTTPS in production
- **Permissions Policy**: Restricts browser features

### 6. Rate Limiting

- **API Rate Limiting**: Prevents abuse and DoS attacks
- **Upload Rate Limiting**: Separate limits for file uploads
- **Configurable Limits**: Can be adjusted based on requirements

### 7. CORS Configuration

- **Restricted Origins**: Only specified origins are allowed
- **Configurable Origins**: Environment variable controlled
- **Credential Handling**: Secure credential passing

### 8. Error Handling

- **Information Disclosure Prevention**: Error messages don't reveal sensitive information
- **Security Event Logging**: Failed authentication attempts are logged
- **Graceful Degradation**: Secure fallbacks for error conditions

## Configuration

### Environment Variables

```bash
# Required for production
DASHLY_API_KEY=your-secure-random-key-here  # Min 16 chars
REQUIRE_AUTH=true

# Optional configuration
ALLOWED_ORIGINS=https://yourdomain.com
MAX_REQUESTS_PER_HOUR=100
MAX_UPLOADS_PER_HOUR=10
```

### Generating Secure API Keys

```python
import secrets
api_key = secrets.token_urlsafe(32)
print(f"DASHLY_API_KEY={api_key}")
```

## Security Best Practices

### For Development

1. Use `.env.development` for local development
2. Never commit real API keys to version control
3. Use authentication bypass only in isolated development environments
4. Regularly update dependencies

### For Production

1. Always set `REQUIRE_AUTH=true`
2. Use strong, randomly generated API keys
3. Enable HTTPS with proper certificates
4. Configure proper CORS origins
5. Monitor security logs regularly
6. Implement proper backup and recovery procedures

### For Database Operations

1. All queries are validated before execution
2. Only SELECT operations are allowed
3. Parameterized queries prevent SQL injection
4. Sample data is sanitized to prevent information disclosure

## Vulnerability Reporting

If you discover a security vulnerability, please:

1. Do not create a public issue
2. Contact the development team privately
3. Provide detailed information about the vulnerability
4. Allow time for the issue to be addressed before disclosure

## Security Testing

Run the security test suite:

```bash
cd backend
python -m pytest src/test_security_fixes.py -v
```

## Compliance Notes

- Input validation follows OWASP guidelines
- SQL injection prevention uses multiple layers of protection
- Authentication follows industry best practices
- Error handling prevents information disclosure
- Logging includes security event monitoring

## Regular Security Tasks

1. **Weekly**: Review security logs for anomalies
2. **Monthly**: Update dependencies and scan for vulnerabilities
3. **Quarterly**: Review and rotate API keys
4. **Annually**: Conduct comprehensive security audit

## Known Limitations

1. **LLM Integration**: When implemented, ensure proper input sanitization
2. **File Processing**: Large files could impact performance
3. **Rate Limiting**: In-memory implementation doesn't persist across restarts
4. **Session Management**: Simple API key auth may need enhancement for multi-user scenarios

## Security Checklist

- [ ] API keys are properly configured
- [ ] Authentication is enabled in production
- [ ] HTTPS is configured and enforced
- [ ] CORS origins are properly restricted
- [ ] Security headers are enabled
- [ ] Rate limiting is configured
- [ ] Input validation is comprehensive
- [ ] Error messages don't leak information
- [ ] Security logging is enabled
- [ ] Dependencies are up to date
- [ ] Security tests pass
