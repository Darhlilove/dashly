# Dashly Security Guide

## Overview

This document outlines the security measures implemented in Dashly and provides guidance for secure deployment and operation.

## Security Features Implemented

### 1. Authentication & Authorization

- **API Key Authentication**: All endpoints require valid API key authentication
- **Configurable Auth**: Authentication can be disabled for development (not recommended for production)
- **Strong Key Requirements**: API keys must be at least 32 characters long
- **Key Validation**: Automatic validation of API key format and strength

### 2. Input Sanitization & Validation

- **Query Sanitization**: All user queries are sanitized before LLM processing
- **Prompt Injection Protection**: Detection and neutralization of prompt injection attempts
- **SQL Injection Prevention**: Multi-layer SQL injection protection
- **Input Length Limits**: Configurable limits on query and SQL length
- **Character Filtering**: Removal of suspicious control characters

### 3. SQL Security

- **SELECT-Only Queries**: Only SELECT statements are allowed
- **DDL/DML Blocking**: All data definition and manipulation operations are blocked
- **Pattern Detection**: Advanced detection of dangerous SQL patterns
- **Query Complexity Limits**: Prevention of overly complex queries that could indicate obfuscation
- **Table Reference Validation**: Validation that queries only reference expected tables

### 4. Rate Limiting

- **Per-Client Limits**: Individual rate limits per client IP/session
- **Multiple Time Windows**: Per-minute and per-hour limits
- **Token Usage Tracking**: LLM token usage monitoring and limits
- **Cooldown Periods**: Automatic cooldown for clients exceeding limits
- **Failed Request Tracking**: Monitoring of failed requests for abuse detection

### 5. File Upload Security

- **File Type Validation**: Only CSV files are accepted
- **Size Limits**: Configurable file size limits (default: 50MB)
- **Content Validation**: CSV content parsing and validation
- **Path Traversal Protection**: Prevention of directory traversal attacks
- **Atomic File Operations**: Safe file writing with atomic operations

### 6. Network Security

- **CORS Configuration**: Configurable Cross-Origin Resource Sharing
- **Security Headers**: Comprehensive HTTP security headers
- **HTTPS Enforcement**: Optional HTTPS-only mode for production
- **Content Security Policy**: Strict CSP to prevent XSS attacks

### 7. Error Handling & Information Disclosure

- **Sanitized Error Messages**: Error messages don't expose sensitive information
- **Structured Exception Handling**: Consistent error handling across the application
- **Security Event Logging**: Comprehensive logging of security events
- **Failed Attempt Monitoring**: Tracking of failed authentication and validation attempts

## Configuration

### Environment Variables

```bash
# Security Configuration
DASHLY_API_KEY=your_secure_random_key_here  # Generate with: openssl rand -hex 32
REQUIRE_AUTH=true                           # Always true for production
ALLOWED_ORIGINS=https://yourdomain.com      # Restrict to your actual domains

# Rate Limiting
MAX_REQUESTS_PER_HOUR=500
MAX_UPLOADS_PER_HOUR=50

# LLM Security
OPENROUTER_API_KEY=your_openrouter_key_here # Never commit this to version control
```

### Security Configuration File

The `security_config.py` file centralizes all security settings:

```python
# Example security configuration
security_config = SecurityConfig(
    MAX_CSV_SIZE_MB=50,
    MAX_QUERY_LENGTH=500,
    REQUIRE_AUTH=True,
    ENABLE_INPUT_SANITIZATION=True,
    LOG_SECURITY_EVENTS=True
)
```

## Deployment Security Checklist

### Pre-Deployment

- [ ] Generate secure API keys using `openssl rand -hex 32`
- [ ] Set `REQUIRE_AUTH=true`
- [ ] Configure `ALLOWED_ORIGINS` to your actual frontend domains
- [ ] Set `DEBUG=false` and appropriate `LOG_LEVEL`
- [ ] Ensure `.env` files are not committed to version control
- [ ] Review and test all security configurations

### Production Environment

- [ ] Use HTTPS for all communications
- [ ] Set `ENABLE_HTTPS_ONLY=true`
- [ ] Configure proper firewall rules
- [ ] Set up monitoring and alerting for security events
- [ ] Implement log aggregation and analysis
- [ ] Regular security audits and updates

### Monitoring

- [ ] Monitor rate limiting statistics via `/api/security/stats`
- [ ] Set up alerts for suspicious activity patterns
- [ ] Regular review of security logs
- [ ] Monitor LLM API usage and costs

## Security Endpoints

### GET /api/security/stats

Returns security statistics including:

- Input sanitization metrics
- Rate limiting statistics
- Authentication status
- Current security configuration

**Authentication Required**: Yes

## Threat Model

### Threats Mitigated

1. **SQL Injection**: Multi-layer validation and sanitization
2. **Prompt Injection**: LLM input sanitization and validation
3. **Path Traversal**: File path validation and sandboxing
4. **Rate Limiting Abuse**: Comprehensive rate limiting system
5. **Authentication Bypass**: Strong API key requirements
6. **XSS Attacks**: Content Security Policy and output encoding
7. **CSRF Attacks**: Proper CORS configuration
8. **Information Disclosure**: Sanitized error messages

### Residual Risks

1. **LLM Model Vulnerabilities**: Dependent on OpenRouter/model security
2. **DuckDB Vulnerabilities**: Dependent on DuckDB security updates
3. **Dependency Vulnerabilities**: Regular updates required
4. **Social Engineering**: User education required

## Incident Response

### Security Event Types

- **Authentication Failures**: Failed API key attempts
- **Input Validation Failures**: Blocked malicious inputs
- **Rate Limit Violations**: Excessive request patterns
- **File Upload Violations**: Invalid or malicious file uploads
- **SQL Security Violations**: Dangerous query attempts

### Response Procedures

1. **Immediate**: Automatic blocking and logging
2. **Short-term**: Alert administrators and investigate
3. **Long-term**: Update security rules and configurations

## Security Updates

### Regular Tasks

- Update dependencies monthly
- Review security logs weekly
- Rotate API keys quarterly
- Security audit annually

### Emergency Procedures

- Immediate API key rotation if compromised
- Rate limit adjustment for attack mitigation
- Emergency shutdown procedures if needed

## Contact

For security issues or questions:

- Review this documentation
- Check security logs and monitoring
- Implement additional security measures as needed

## Compliance Notes

This implementation includes security measures appropriate for:

- Data protection requirements
- API security best practices
- Input validation standards
- Authentication and authorization controls

Regular security reviews and updates are recommended to maintain security posture.
