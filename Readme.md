# GSpaces Deployment on AWS EC2 (PostgreSQL + Flask + Gunicorn + Nginx + Cloudflare SSL)

## 1. Server Setup
### Update & Install Required Packages
```bash
sudo yum update -y
sudo amazon-linux-extras enable postgresql16
sudo yum install postgresql16 postgresql16-server postgresql16-contrib -y
sudo yum install python3 python3-pip python3-venv git nginx -y
sudo yum install -y nginx
sudo amazon-linux-extras enable python3.8
sudo pip3 install certbot certbot-nginx
sudo yum install cronie -y
sudo systemctl enable crond
sudo systemctl start crond
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
### 12. Create gspaces daemon service
`/etc/systemd/system/gspaces.service`
```
[Unit]
Description=Gunicorn instance for GSpaces
After=network.target

[Service]
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/gspaces_new
ExecStart=/usr/local/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```
Apply changes
```
sudo systemctl daemon-reload
sudo systemctl restart gspaces
sudo systemctl status gspaces
```
### 13. Enable HTTPS with Let’s Encrypt
Run certbot to issue and configure certificates:
```
sudo certbot --nginx -d gspaces.in -d www.gspaces.in
```
    - Auto Renewal
        ```
        sudo crontab -e
        ```
        Insert:
        ```
        0 0 * * * certbot renew --quiet
        ```
        Certbot sets up a system timer to renew certificates automatically.
        Verify with:
        ```
        sudo systemctl list-timers | grep certbot
        ```
    - Test renewal manually:
        ```
        sudo certbot renew --dry-run
        ```
### 14. Configure Nginx for GSpaces
Create a new config file:
```
sudo vim /etc/nginx/conf.d/gspaces.conf
# Redirect all HTTP traffic to HTTPS
server {
    listen 80;
    server_name gspaces.in www.gspaces.in;
    return 301 https://$host$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl;
    server_name gspaces.in www.gspaces.in;

    # SSL Certificates (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/gspaces.in/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gspaces.in/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Logs
    access_log /var/log/nginx/gspaces_access.log;
    error_log /var/log/nginx/gspaces_error.log;

    # Max upload size (adjust as needed)
    client_max_body_size 50M;

    # Proxy to Gunicorn
    location / {
        proxy_pass http://127.0.0.1:5000;  # Gunicorn should run on port 5000 & main.py port 5000
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Run:
```
sudo nginx -t
sudo systemctl restart nginx
```

### 15. Cloudflare Configuration

### 🔹 DNS Settings
1. Go to **Cloudflare → DNS**.
2. Add the following records:
   - **A Record** → `gspaces.in` → Public IP of EC2 → **Proxy ON (orange cloud)**
   - **A Record** → `www.gspaces.in` → Same IP → **Proxy ON (orange cloud)**

---

### 🔹 SSL/TLS Settings
1. Go to **Cloudflare → SSL/TLS**.
2. Set SSL/TLS mode to **Full (Strict) ✅**  
   (This ensures Cloudflare validates your Let’s Encrypt certificate on the server.)

---

### 🔹 Page Rules (Optional)
- Add a redirect rule:  
  `http://gspaces.in/*` → `https://gspaces.in/$1`  

👉 This is optional since Nginx already forces HTTP → HTTPS.

---

### 🔹 Firewall
- In your **AWS Security Group**, allow inbound traffic on:
  - **Port 80 (HTTP)**
  - **Port 443 (HTTPS)**


