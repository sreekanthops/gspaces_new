CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    price NUMERIC,
    rating NUMERIC,
    image_url TEXT
);


gspaces=> select * from products;
 id | name | description | category  | price | rating |         image_url       
   | created_by 

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
