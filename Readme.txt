sudo nginx -t && sudo systemctl reload nginx
# Kill any existing
sudo fuser -k 8000/tcp

# Start fresh from /var/www/gspaces
cd /var/www/gspaces
source venv/bin/activate
gunicorn -w 4 -b 127.0.0.1:8000 main:app
