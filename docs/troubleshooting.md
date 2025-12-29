# Troubleshooting Guide

## Common Issues

### Database Connection Errors

**Symptom**: `could not connect to server: Connection refused`

**Solutions**:
1. Check if PostgreSQL is running:
   ```bash
   docker-compose ps postgres
   ```

2. Verify DATABASE_URL in `.env`:
   ```env
   DATABASE_URL=postgresql://exhibidores:password@postgres:5432/exhibidores_db
   ```

3. Check PostgreSQL logs:
   ```bash
   docker-compose logs postgres
   ```

### Redis Connection Errors

**Symptom**: `Error connecting to Redis`

**Solutions**:
1. Check if Redis is running:
   ```bash
   docker-compose ps redis
   ```

2. Test Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

### Twilio SMS Not Sending

**Symptom**: OTP codes not received

**Solutions**:
1. Verify Twilio credentials in `.env`
2. Check Twilio account balance
3. Verify phone number format (E.164: +573001234567)
4. Check backend logs:
   ```bash
   docker-compose logs backend | grep -i twilio
   ```

### MinIO Upload Failures

**Symptom**: `Error uploading photo`

**Solutions**:
1. Check MinIO is running:
   ```bash
   docker-compose ps minio
   ```

2. Verify bucket exists:
   ```bash
   docker-compose exec minio mc ls minio/exhibidores
   ```

3. Create bucket if missing:
   ```bash
   docker-compose exec minio mc mb minio/exhibidores
   ```

### Frontend Not Loading

**Symptom**: Blank page or connection errors

**Solutions**:
1. Check if backend is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify VITE_API_URL in frontend build:
   ```bash
   docker-compose logs frontend
   ```

3. Clear browser cache and reload

### Migrations Failing

**Symptom**: `alembic upgrade head` fails

**Solutions**:
1. Check current migration version:
   ```bash
   docker-compose exec backend alembic current
   ```

2. Reset database (CAUTION: deletes all data):
   ```bash
   docker-compose down -v
   docker-compose up -d postgres
   docker-compose exec backend alembic upgrade head
   ```

3. Check migration files for syntax errors

### Worker Not Processing Jobs

**Symptom**: Notifications not sent

**Solutions**:
1. Check worker logs:
   ```bash
   docker-compose logs worker
   ```

2. Verify Redis connection:
   ```bash
   docker-compose exec worker python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"
   ```

3. Restart worker:
   ```bash
   docker-compose restart worker
   ```

### High Memory Usage

**Solutions**:
1. Check container stats:
   ```bash
   docker stats
   ```

2. Adjust memory limits in `docker-compose.yml`:
   ```yaml
   services:
     backend:
       mem_limit: 512m
   ```

3. Optimize database queries with EXPLAIN ANALYZE

### Slow API Responses

**Solutions**:
1. Enable query logging:
   ```python
   # app/database.py
   engine = create_async_engine(database_url, echo=True)
   ```

2. Add database indexes for slow queries

3. Enable Redis caching for frequently accessed data

4. Use connection pooling (already configured)

### Permission Denied Errors

**Symptom**: `Permission denied` in Docker

**Solutions**:
1. Fix file permissions:
   ```bash
   sudo chown -R $USER:$USER .
   ```

2. Run with sudo (not recommended):
   ```bash
   sudo docker-compose up
   ```

### Port Already in Use

**Symptom**: `port is already allocated`

**Solutions**:
1. Find process using port:
   ```bash
   # Linux/Mac
   lsof -i :8000
   
   # Windows
   netstat -ano | findstr :8000
   ```

2. Kill process or change port in `docker-compose.yml`

## Debugging Tips

### Enable Debug Mode

```env
DEBUG=true
ENVIRONMENT=development
```

### View All Logs

```bash
docker-compose logs -f --tail=100
```

### Access Database

```bash
docker-compose exec postgres psql -U exhibidores exhibidores_db
```

### Access Redis CLI

```bash
docker-compose exec redis redis-cli
```

### Test API Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Request OTP
curl -X POST http://localhost:8000/auth/otp/request \
  -H "Content-Type: application/json" \
  -d '{"phone": "+573001234567", "full_name": "Test User"}'
```

### Check Celery Tasks

```bash
docker-compose exec worker celery -A app.worker.celery_app inspect active
```

## Getting Help

1. Check logs first: `docker-compose logs`
2. Review documentation in `/docs`
3. Search GitHub issues
4. Contact support: soporte@ejemplo.com

## Performance Monitoring

### Enable Prometheus Metrics

```env
ENABLE_PROMETHEUS=true
```

Access metrics at: http://localhost:8000/metrics

### Database Query Performance

```sql
-- Slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### Redis Memory Usage

```bash
docker-compose exec redis redis-cli INFO memory
```
