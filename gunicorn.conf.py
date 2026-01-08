# Gunicorn 生产服务器配置

import multiprocessing

# 绑定地址
bind = "0.0.0.0:5000"

# 工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "sync"

# 超时设置
timeout = 120
keepalive = 5

# 日志
accesslog = "-"
errorlog = "-"
loglevel = "info"

# 进程名
proc_name = "deeptrender"

# 重载（仅开发模式）
reload = False

# 预加载应用
preload_app = True
