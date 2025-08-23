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
sudo pip3 install certbot certbot-nginx flask_mail authlib google-auth google-auth-oauthlib google-auth-httplib2 flask psycopg2-binary 
sudo yum install cronie -y
sudo systemctl enable crond
sudo systemctl start crond
sudo chown -R ec2-user:ec2-user static/img/Products
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



## Table of Contents

<!-- ... (Rest of your Table of Contents) ... -->

5.  [Troubleshooting](#troubleshooting)
    *   [Common Issues & Solutions](#common-issues--solutions)
    *   [File & Directory Permissions](#file--directory-permissions)
    *   [Nginx & Gunicorn Logs](#nginx--gunicorn-logs)

## Troubleshooting

This section provides guidance on common issues encountered during deployment and operation, with a focus on file permissions.

### Common Issues & Solutions

*   **"Not Found" (404) for `sitemap.xml`, `robots.txt`, or Static Files (CSS/JS/Images):**
    *   **Cause:** Nginx cannot find the file where it expects it, or lacks permission to read it.
    *   **Solution:**
        1.  **Verify File Existence:** Ensure the file (`sitemap.xml`, `robots.txt`, or your static assets) is physically located in the correct directory on the server (e.g., `/home/ec2-user/gspaces/sitemap.xml` for `sitemap.xml`, `/home/ec2-user/gspaces/static/css/main.css` for a CSS file).
        2.  **Check Nginx `root` Directive:** Ensure the `root` directive in your Nginx configuration points to the correct base directory of your project (`/home/ec2-user/gspaces/`).
        3.  **Review Nginx `location` Blocks:** Verify that the `location` blocks for `/sitemap.xml`, `/robots.txt`, and `/static/` (if used) are correctly defined and point to the right places, and that their `try_files` directives are correct.
        4.  **Check Permissions:** This is a very common cause. See [File & Directory Permissions](#file--directory-permissions) below.

*   **"Permission denied" errors in Nginx logs:**
    *   **Cause:** The Nginx user (commonly `nginx` or `www-data`) does not have the necessary read or execute permissions on a file or directory.
    *   **Solution:** Adjust file and directory permissions. See [File & Directory Permissions](#file--directory-permissions) below.

*   **"502 Bad Gateway" / "Connection refused" when accessing the app:**
    *   **Cause:** Nginx cannot connect to your Gunicorn application.
    *   **Solution:**
        1.  **Check Gunicorn Status:** Ensure your Gunicorn service is running (`sudo systemctl status gspaces`).
        2.  **Verify Socket Path:** Confirm the `proxy_pass` in Nginx (e.g., `http://unix:/home/ec2-user/gspaces/gspaces.sock;`) matches the `bind` path in your Gunicorn service file.
        3.  **Socket Permissions:** Ensure the Gunicorn socket file (`gspaces.sock`) has permissions that allow Nginx to connect (e.g., `chmod 666` or ensure Nginx user is in the correct group).

*   **"500 Internal Server Error" (after Flask code changes):**
    *   **Cause:** An error within your Flask application code.
    *   **Solution:** Check your Gunicorn service logs (`sudo journalctl -u gspaces.service -f`) for Python tracebacks.

### File & Directory Permissions

Incorrect file permissions are a frequent source of deployment issues. Nginx needs to be able to **read** files it serves and **execute** (traverse) directories leading to those files.

**General Guidelines:**

*   **Files:** `644` (owner read/write, group read, others read)
*   **Directories:** `755` (owner read/write/execute, group read/execute, others read/execute)

**How to Check and Fix:**

1.  **Connect to your server via SSH.**
2.  **Navigate to your project root:**
    ```bash
    cd /home/ec2-user/gspaces
    ```

3.  **Check and set permissions for critical files:**
    *   **`robots.txt`:**
        ```bash
        ls -l robots.txt
        sudo chmod 644 robots.txt
        ```
    *   **`sitemap.xml`:**
        ```bash
        ls -l sitemap.xml
        sudo chmod 644 sitemap.xml
        ```
    *   **Static files (e.g., CSS, JS, images):**
        ```bash
        ls -l static/css/main.css # Check specific file
        # To apply to all static files and directories (use with caution):
        # sudo find static/ -type f -exec chmod 644 {} +
        # sudo find static/ -type d -exec chmod 755 {} +
        ```
        (It's safer to apply `chmod 644` to individual static files and `chmod 755` to their containing directories as needed.)

4.  **Check and set permissions for directories:**
    Nginx needs `x` (execute) permission for "others" on every directory in the path leading to your files.

    *   **Your project root (`gspaces` directory):**
        ```bash
        ls -ld /home/ec2-user/gspaces/
        sudo chmod 755 /home/ec2-user/gspaces/
        ```
    *   **Your home directory (`ec2-user` directory):**
        This is a common oversight. If `/home/ec2-user/` has restrictive permissions (e.g., `700`), Nginx cannot traverse into it.
        ```bash
        ls -ld /home/ec2-user/
        sudo chmod 755 /home/ec2-user/
        ```
    *   **`static` directory (if you're serving static files via Nginx):**
        ```bash
        ls -ld static/
        sudo chmod 755 static/
        ```

### Nginx & Gunicorn Logs

Logs are your best friends for debugging.

*   **Nginx Error Logs:**
    *   **Location:** `/var/log/nginx/gspaces_error.log` (as defined in your Nginx config)
    *   **Command:** `sudo tail -f /var/log/nginx/gspaces_error.log`
    *   **Purpose:** Shows errors Nginx encounters, such as "permission denied," "no such file or directory," or issues connecting to Gunicorn. Check this first for any 404s on static files, sitemap, or robots.txt.

*   **Nginx Access Logs:**
    *   **Location:** `/var/log/nginx/gspaces_access.log` (as defined in your Nginx config)
    *   **Command:** `sudo tail -f /var/log/nginx/gspaces_access.log`
    *   **Purpose:** Shows all requests Nginx processes, along with their HTTP status codes. Useful for confirming if a request is even reaching Nginx and what status code it's returning (e.g., 200 OK, 404 Not Found, 500 Internal Server Error).

*   **Gunicorn Service Logs:**
    *   **Command:** `sudo journalctl -u gspaces.service -f`
    *   **Purpose:** Shows output from your Gunicorn process, including Python tracebacks for application errors, startup/shutdown messages, and any `print()` statements from your Flask app. Use this when Nginx reports a 502 Bad Gateway or when your application is crashing.

---


