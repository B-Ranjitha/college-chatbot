# gunicorn.conf.py — Production server configuration

import multiprocessing

# Server socket
bind = "0.0.0.0:5000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "-"
errorlog  = "-"
loglevel  = "info"
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sµs'

# Process naming
proc_name = "bbc_college_chatbot"

# Server mechanics
daemon = False
preload_app = True
forwarded_allow_ips = "*"
