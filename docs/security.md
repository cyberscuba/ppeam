# Security Best Practices

## Authentication

### Passwordless OTP
- 6-digit codes with 5-minute expiration
- Maximum 3 attempts per code
- Rate limiting: 3 OTP requests per hour per phone
- Rate limiting: 10 OTP requests per day per IP

### JWT Tokens
- Short-lived access tokens (15 minutes)
- Refresh tokens stored hashed in database
- Token revocation support
- Device tracking optional

## Input Validation

### Phone Numbers
- E.164 format validation using `phonenumbers` library
- Example: +573001234567

### SQL Injection Prevention
- SQLAlchemy ORM with parameterized queries
- No raw SQL execution without sanitization

### XSS Prevention
- React automatically escapes output
- CSP headers configured
- No `dangerouslySetInnerHTML` usage

## Rate Limiting

### API Endpoints
- Global: 60 requests/minute per IP
- OTP request: 3/hour per phone, 10/day per IP
- Login: 5 attempts/minute per IP

### Implementation
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.get("/api/endpoint")
@limiter.limit("10/minute")
async def endpoint():
    pass
```

## HTTPS/TLS

### Production Requirements
- HTTPS mandatory (HSTS header)
- TLS 1.2+ only
- Strong cipher suites

### Certificate Setup
```bash
sudo certbot --nginx -d tu-dominio.com
```

## Security Headers

### Configured Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Database Security

### Connection
- SSL/TLS for database connections in production
- Separate read-only user for reports
- Connection pooling with limits

### Encryption
- Passwords hashed with bcrypt (if used)
- Sensitive data encrypted at rest
- Backup encryption

### Example
```python
# Use SSL in production
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

## File Upload Security

### Validation
- File type whitelist (images only)
- File size limit (10MB)
- Virus scanning (optional)
- Unique filenames (UUID)

### Storage
- S3/MinIO with private buckets
- Signed URLs for access
- No direct file system access

## Secrets Management

### Environment Variables
- Never commit `.env` to git
- Use secrets management in production (AWS Secrets Manager, Vault)
- Rotate secrets regularly

### Example
```bash
# Generate secure JWT secret
openssl rand -hex 32
```

## Audit Logging

### What to Log
- Authentication attempts
- Admin actions
- Request approvals/rejections
- Configuration changes
- Failed authorization attempts

### Log Format
```json
{
  "actor_id": "uuid",
  "action": "request_approved",
  "target": {"request_id": "uuid"},
  "ip_address": "1.2.3.4",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## GDPR Compliance

### Data Retention
- Default: 365 days
- Configurable via `app_settings`
- Automated cleanup script

### User Rights
- Right to access data
- Right to deletion
- Right to data portability
- Consent for WhatsApp notifications

### Implementation
```sql
-- Delete user data
DELETE FROM users WHERE id = 'user_id';
-- Cascades to related tables
```

## Dependency Security

### Scanning
```bash
# Python
pip install safety
safety check

# Node.js
npm audit
```

### Updates
- Regular dependency updates
- Automated security patches
- CI/CD security scans

## Network Security

### Firewall Rules
```bash
# Allow only necessary ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 22/tcp
ufw enable
```

### Docker Network
- Isolated Docker network
- No exposed internal ports
- Reverse proxy (nginx/traefik)

## Monitoring & Alerts

### Security Events
- Failed login attempts
- Rate limit violations
- Unauthorized access attempts
- Unusual activity patterns

### Alerting
```python
# Send alert on suspicious activity
if failed_attempts > 10:
    send_alert_email(admin_email, "Suspicious activity detected")
```

## Incident Response

### Steps
1. Identify and contain
2. Investigate and analyze
3. Eradicate threat
4. Recover systems
5. Post-incident review

### Contacts
- Security team: security@ejemplo.com
- On-call: +57 300 123 4567

## Security Checklist

- [ ] HTTPS enabled with valid certificate
- [ ] Strong JWT secret (32+ characters)
- [ ] Database SSL enabled
- [ ] Rate limiting configured
- [ ] Security headers set
- [ ] Input validation on all endpoints
- [ ] Audit logging enabled
- [ ] Secrets not in code/git
- [ ] Dependencies up to date
- [ ] Backups encrypted
- [ ] Monitoring and alerting active
- [ ] Incident response plan documented

## Penetration Testing

### Recommended Tools
- OWASP ZAP
- Burp Suite
- sqlmap
- nmap

### Schedule
- Quarterly automated scans
- Annual professional audit

## Reporting Vulnerabilities

Email: security@ejemplo.com

Please include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

We aim to respond within 48 hours.
