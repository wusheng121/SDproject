# ADR-0001: Production baseline for member A

## Status

Accepted

## Context

The project moved from a movie recommendation demo to a campus second-hand marketplace. Authentication, RBAC, database schema and the admin console must be safe to operate outside a classroom demo.

## Decisions

1. MySQL 8.0+ is the only production database. SQLite is allowed only for isolated tests.
2. Schema changes use Alembic. Application startup never calls `create_all` in production.
3. Access tokens are short-lived and kept in memory. Refresh tokens are opaque, hashed at rest, rotated, and stored in an HttpOnly cookie.
4. Authorization is RBAC-first. `user_type` is retained for compatibility but roles are the source of truth.
5. Passwords use BCrypt cost 12. Phone numbers are encrypted at rest, indexed with a blind hash, and masked in every response.
6. Audit records are append-only through the API. Admin writes and Agent reads record actor, resource, IP, user agent and trace id.
7. Agent access uses hashed API keys with explicit scopes instead of interactive passwords.
8. API v1 uses a stable error envelope and cursor-free pagination (`page`, `page_size`, `total`).
9. Production requires Redis for rate limiting and cache, and explicit CORS allowlists.
10. Docker Compose is the local integration environment; production uses a Docker image plus managed MySQL/Redis.

## Consequences

- Old SQLite data is not migrated; seed data is development-only.
- Existing `/api` product endpoints remain during the transition, while member A endpoints live under `/api/v1`.
- SMS verification is not part of the first implementation; email verification is used instead until the product decision changes.
