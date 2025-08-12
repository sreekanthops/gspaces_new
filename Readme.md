# PostgreSQL 16 Setup on Amazon Linux 2023

This guide explains how to install, initialize, and verify PostgreSQL 16 on an Amazon Linux 2023 EC2 instance.  
It ends with a working PostgreSQL instance and a version check query.

---

## 1. Install PostgreSQL 16

```bash
sudo dnf install postgresql16 postgresql16-server -y
```
### 2. Initialize the Database Cluster
Amazon Linux's postgresql.service expects `PGDATA=/var/lib/pgsql/data`

```bash
# Remove any existing or empty data directory
sudo rm -rf /var/lib/pgsql/data

# Initialize database cluster
sudo -u postgres /usr/bin/initdb -D /var/lib/pgsql/data
```

Expected output should end with:
```
Success. You can now start the database server using:
    /usr/bin/pg_ctl -D /var/lib/pgsql/data -l logfile start
```

### 3. Enable and Start PostgreSQL
```
sudo systemctl enable --now postgresql
```

Check status:
```
sudo systemctl status postgresql
```
Service should be active (running).

### 4. Verify Installation
Run
```
sudo -u postgres psql -c "SELECT version();"
```
Expected output:
```
                                                   version                                                    
--------------------------------------------------------------------------------------------------------------
 PostgreSQL 16.9 on x86_64-amazon-linux-gnu, compiled by gcc ...
(1 row)

```

### Notes
Default authentication for local connections is trust (no password).

# Project Setup Guide – Amazon Linux + PostgreSQL 16 + Flask

### 1. Update and Install Dependencies
```bash
sudo yum update -y
sudo yum install -y gcc python3 python3-pip python3-devel postgresql16 postgresql16-server postgresql16-devel
```

###  2. Initialize PostgreSQL 16 Database
```
sudo /usr/bin/postgresql-16-setup initdb
```

###  3. Configure PostgreSQL Systemd Service
Amazon Linux’s default postgresql.service points to `/var/lib/pgsql/data`
but PostgreSQL 16 initializes in `/var/lib/pgsql/16/data`
We’ll point the default service to the correct directory:
```
sudo mv /var/lib/pgsql/16/data /var/lib/pgsql/data
sudo chown -R postgres:postgres /var/lib/pgsql/data
```

###  4. Start PostgreSQL
```
sudo systemctl enable --now postgresql
```

###  5. Verify PostgreSQL is Running
```
sudo -u postgres psql -c "SELECT version();"
```
You should see something like:
```
PostgreSQL 16.9 on x86_64-amazon-linux-gnu, compiled by gcc ...
```

###  6. Install Python Dependencies
```
pip install flask psycopg2-binary
```

### 7. Create Database and User
```
sudo -u postgres psql
```
Run:
```
CREATE DATABASE gspaces;
CREATE ROLE sri WITH LOGIN PASSWORD 'gspaces';
GRANT ALL PRIVILEGES ON DATABASE gspaces TO sri;
\q
```

### 8. Restore Database from `.sql` File
If your SQL file contains references to missing users, create them first as shown above.
Restore:
```
psql -U postgres -d gspaces -f gspaces_backup.sql
```

### 9. Validate Database
Login:
```
psql -U postgres -d gspaces
```
Check tables:
```
\dt
```

Check data:
```
SELECT * FROM your_table LIMIT 5;
```

### 10. View Users & Passwords (hashed)
```
sudo -u postgres psql -c "\du"
```
View hashed passwords (superuser only):
```
sudo -u postgres psql -c "SELECT rolname, rolpassword FROM pg_authid;"
```
Change password:
```
sudo -u postgres psql -c "ALTER ROLE sri WITH PASSWORD 'newpassword';"
```

### 11. Run Flask Application
```
python main.py
```
If you want to run on browser for external access:
```
app.run(host='0.0.0.0', port=5000, debug=True)
```
Access at:
```
http://<EC2-Public-IP>:5000
```

