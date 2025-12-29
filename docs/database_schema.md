# Database Schema

## Tables

### users
Stores user information for passwordless authentication.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| full_name | TEXT | User's full name |
| phone | VARCHAR(20) | Phone number (E.164 format) |
| email | VARCHAR(255) | Optional email |
| device_id | VARCHAR(255) | Optional device identifier |
| whatsapp_opt_in | BOOLEAN | WhatsApp notifications consent |
| is_active | BOOLEAN | Account status |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### admins
Admin users with elevated permissions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| role | VARCHAR(50) | Admin role (super_admin, admin) |
| created_at | TIMESTAMP | Creation timestamp |

### points
Exhibition points/locations.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| code | VARCHAR(50) | Unique point code (P001-P040) |
| name | TEXT | Point name |
| description | TEXT | Point description |
| latitude | NUMERIC | GPS latitude |
| longitude | NUMERIC | GPS longitude |
| is_active | BOOLEAN | Active status |
| photo_url | TEXT | Photo URL in S3/MinIO |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### schedules
Time schedules for each point.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| point_id | UUID | Foreign key to points |
| weekday | INT | Day of week (0-6, NULL for all) |
| start_time | TIME | Schedule start time |
| end_time | TIME | Schedule end time |
| is_active | BOOLEAN | Active status |
| created_at | TIMESTAMP | Creation timestamp |

### slots
Specific time slots generated from schedules.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| point_id | UUID | Foreign key to points |
| schedule_id | UUID | Foreign key to schedules |
| slot_date | DATE | Slot date |
| start_ts | TIMESTAMP | Slot start timestamp |
| end_ts | TIMESTAMP | Slot end timestamp |
| capacity | INT | Slot capacity (default 1) |
| created_at | TIMESTAMP | Creation timestamp |

**Unique constraint**: (point_id, schedule_id, slot_date, start_ts)

### requests
User requests for slot assignments.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| status | VARCHAR(30) | pending, approved, rejected, partial |
| notes | TEXT | Optional notes |
| created_at | TIMESTAMP | Creation timestamp (priority) |
| updated_at | TIMESTAMP | Last update timestamp |

### request_items
Individual slot requests within a request.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| request_id | UUID | Foreign key to requests |
| slot_id | UUID | Foreign key to slots (UNIQUE) |
| status | VARCHAR(30) | pending, approved, rejected |
| assigned_at | TIMESTAMP | Assignment timestamp |
| assigned_by | UUID | Foreign key to admins |
| created_at | TIMESTAMP | Creation timestamp |

**Unique constraint**: slot_id (ensures one assignment per slot)

### otp_codes
One-time password codes for authentication.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| phone | VARCHAR(20) | Phone number |
| code | VARCHAR(10) | 6-digit OTP code |
| purpose | VARCHAR(50) | Code purpose (login) |
| attempts | INT | Verification attempts |
| created_at | TIMESTAMP | Creation timestamp |
| expires_at | TIMESTAMP | Expiration timestamp |

### refresh_tokens
Refresh tokens for JWT authentication.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| token_hash | VARCHAR(255) | Hashed token (UNIQUE) |
| device_id | VARCHAR(255) | Device identifier |
| is_revoked | BOOLEAN | Revocation status |
| created_at | TIMESTAMP | Creation timestamp |
| expires_at | TIMESTAMP | Expiration timestamp |

### notifications
Notification log (SMS/WhatsApp).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to users |
| channel | VARCHAR(20) | sms, whatsapp |
| type | VARCHAR(50) | Notification type |
| external_id | TEXT | External service ID |
| payload | JSONB | Message payload |
| status | VARCHAR(20) | pending, sent, failed |
| created_at | TIMESTAMP | Creation timestamp |

### audit_logs
Audit trail for all actions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| actor_id | UUID | User/admin ID |
| actor_type | VARCHAR(20) | user, admin, system |
| action | VARCHAR(100) | Action performed |
| target | JSONB | Target object |
| meta | JSONB | Additional metadata |
| ip_address | VARCHAR(45) | IP address |
| user_agent | TEXT | User agent string |
| created_at | TIMESTAMP | Creation timestamp |

### app_settings
Application configuration.

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Setting key (PRIMARY KEY) |
| value | JSONB | Setting value |
| updated_at | TIMESTAMP | Last update timestamp |

## Indexes

- `idx_users_phone` ON users(phone)
- `idx_users_active` ON users(is_active)
- `idx_points_active` ON points(is_active)
- `idx_slots_point_date` ON slots(point_id, slot_date)
- `idx_slots_date` ON slots(slot_date)
- `idx_requests_user` ON requests(user_id)
- `idx_requests_status` ON requests(status)
- `idx_request_items_slot` ON request_items(slot_id)
- `idx_request_items_request` ON request_items(request_id)
- `idx_otp_phone` ON otp_codes(phone)
- `idx_otp_expires` ON otp_codes(expires_at)
- `idx_notifications_user` ON notifications(user_id)
- `idx_audit_actor` ON audit_logs(actor_id)
- `idx_audit_created` ON audit_logs(created_at)

## Relationships

```
users 1---* requests
users 1---1 admins
points 1---* schedules
points 1---* slots
schedules 1---* slots
requests 1---* request_items
slots 1---1 request_items (via unique constraint)
admins 1---* request_items (assigned_by)
```

## Concurrency Control

The system uses a **unique constraint on `request_items.slot_id`** to prevent double-booking:

1. When a user creates a request, the system attempts to insert request_items
2. If another user already claimed the slot, the INSERT fails with IntegrityError
3. The first request (by `created_at`) wins
4. Conflicting slots are returned with HTTP 409

This approach is simpler and more reliable than SELECT FOR UPDATE locks.
