import os

# Render and cloud platforms pass the listening port in the PORT environment variable
port = os.getenv('PORT', '5000')
bind = f"0.0.0.0:{port}"

workers = 2
threads = 4
timeout = 120
keepalive = 5
accesslog = '-'
errorlog = '-'
