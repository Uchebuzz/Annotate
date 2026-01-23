# PostgreSQL Database Setup Guide

This application now uses PostgreSQL for user authentication and sign-in tracking instead of JSON files.

## Features

- **User Management**: All users are stored in PostgreSQL
- **Sign-in Tracking**: Every user sign-in is logged with timestamp, IP address, and user agent
- **Secure Authentication**: Passwords are hashed using bcrypt
- **Session History**: View sign-in history for users

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose, which automatically sets up both PostgreSQL and the application:

### 1. Create Environment File

Create a `.env` file in the project root:

```env
# Database Configuration
DB_HOST=postgres
DB_PORT=5432
DB_NAME=annotation_db
DB_USER=postgres
DB_PASSWORD=your_secure_password_here

# Admin Password (for initial admin user)
ADMIN_PASSWORD=CHANGE_ME_ON_FIRST_LOGIN
```

### 2. Start Services

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL database
- Start the Streamlit application
- Automatically initialize the database schema
- Create default admin user (if no users exist)

### 3. Access the Application

Open your browser to: `http://localhost:8501`

## Manual Setup (Without Docker)

### 1. Install PostgreSQL

Install PostgreSQL on your system:
- **Windows**: Download from https://www.postgresql.org/download/windows/
- **Mac**: `brew install postgresql` or download from https://www.postgresql.org/download/macosx/
- **Linux**: `sudo apt-get install postgresql` (Ubuntu/Debian) or use your distribution's package manager

### 2. Create Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE annotation_db;

# Create user (optional, or use existing postgres user)
CREATE USER annotation_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE annotation_db TO annotation_user;

# Exit
\q
```

### 3. Configure Environment Variables

Create a `.env` file:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=annotation_db
DB_USER=postgres
DB_PASSWORD=your_password
ADMIN_PASSWORD=CHANGE_ME_ON_FIRST_LOGIN
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
python test_db_connection.py
```

This will:
- Test the database connection
- Initialize the schema
- Create default admin user

### 6. Run the Application

```bash
streamlit run app.py
```

## Migration from JSON to PostgreSQL

If you have existing users in `users.json`, you can migrate them:

### 1. Run Migration Script

```bash
python migrate_users_to_db.py
```

This will:
- Create a backup of `users.json`
- Migrate all users to PostgreSQL
- Preserve password hashes and user data

### 2. Verify Migration

Check that all users were migrated successfully:

```bash
python test_db_connection.py
```

## Database Schema

### Users Table

Stores user accounts:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'tester',
    user_id VARCHAR(255) NOT NULL,
    password_changed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### User Sessions Table

Tracks user sign-ins:

```sql
CREATE TABLE user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    username VARCHAR(255) NOT NULL,
    login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_timestamp TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

## Viewing Sign-in History

You can query sign-in history using the database or add functionality to the admin dashboard:

```python
from auth import get_signin_history

# Get all sign-ins
all_signins = get_signin_history(limit=100)

# Get sign-ins for specific user
user_signins = get_signin_history(username="admin", limit=50)
```

## Troubleshooting

### Database Connection Failed

1. **Check PostgreSQL is running:**
   ```bash
   # Linux/Mac
   sudo systemctl status postgresql
   
   # Windows
   # Check Services panel
   ```

2. **Verify connection settings in `.env`:**
   - Check `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`

3. **Test connection:**
   ```bash
   python test_db_connection.py
   ```

### Docker Compose Issues

1. **Check if containers are running:**
   ```bash
   docker-compose ps
   ```

2. **View logs:**
   ```bash
   docker-compose logs postgres
   docker-compose logs annotation-tool
   ```

3. **Restart services:**
   ```bash
   docker-compose restart
   ```

### Migration Issues

If migration fails:

1. Check the backup file was created: `users.json.backup.*`
2. Verify database connection is working
3. Check that users.json is valid JSON
4. Run migration again (it will skip existing users)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `annotation_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | `postgres` |
| `ADMIN_PASSWORD` | Initial admin password | `CHANGE_ME_ON_FIRST_LOGIN` |

## Security Notes

1. **Change Default Passwords**: Always change `ADMIN_PASSWORD` and `DB_PASSWORD` in production
2. **Use Strong Passwords**: Use complex passwords for database and admin accounts
3. **Secure `.env` File**: Never commit `.env` to version control (already in `.gitignore`)
4. **Database Access**: Restrict database access to only the application server
5. **Backup Regularly**: Set up regular backups of the PostgreSQL database

## Backup and Restore

### Backup Database

```bash
# Using pg_dump
pg_dump -U postgres annotation_db > backup.sql

# Using Docker
docker exec pidgin-postgres pg_dump -U postgres annotation_db > backup.sql
```

### Restore Database

```bash
# Using psql
psql -U postgres annotation_db < backup.sql

# Using Docker
docker exec -i pidgin-postgres psql -U postgres annotation_db < backup.sql
```

## Next Steps

- Add sign-in history view to admin dashboard
- Set up automated database backups
- Configure connection pooling for production
- Add database monitoring and alerts

