# Security Strategy & Hardening Guidelines

## 1. Malware and Upload Security
- **File Validation**: All uploaded files are strictly verified for accepted MIME types (`text/csv`, `application/vnd.ms-excel`, `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/json`).
- **Size Limitations**: Upload streams enforce a hard size limit (50MB) via application-level buffering to prevent Denial of Service (DoS) attacks.
- **Malware Scanning Strategy (Future)**: In a production environment, all uploads will be offloaded to an S3 bucket configured with an asynchronous ClamAV Lambda function before being processed by the application core.

## 2. API Protection
- **Rate Limiting**: Critical endpoints (e.g., `/api/v1/auth/login`, `/api/v1/materials/upload`) are rate-limited using `slowapi` to mitigate brute-force attempts and abuse.
- **CORS Strategy**: Cross-Origin Resource Sharing is restricted. In production environments, `allow_origins` must exclusively whitelist internal corporate domains.
- **Security Headers**: All API responses enforce strict browser headers (HSTS, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `X-XSS-Protection`) via dedicated middleware.

## 3. Input Validation & Injection Prevention
- **SQL Injection**: SQLAlchemy ORM parameterization intrinsically prevents raw SQL injection attacks. Direct string interpolation into queries is prohibited.
- **XSS Protection**: Frontend components (React) automatically sanitize rendering variables. Backend inputs are explicitly verified against Pydantic models.
- **CSRF Strategy**: The application uses stateless JWT Bearer tokens passed via headers, nullifying traditional cookie-based CSRF vulnerabilities.

## 4. Secret & Logging Management
- **Error Sanitization**: Backend global exception handlers explicitly mask stack traces and unhandled `Exception` strings from the end-user API responses to prevent environmental leakage.
- **Dependency Scanning**: Dependencies are to be routinely audited using `pip-audit` for Python and `npm audit` for the React client.
- **Secure Logging**: Personally Identifiable Information (PII) and raw passwords are never emitted to application logs.
