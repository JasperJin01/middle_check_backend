
项目部署
``` shell
# 后端框架
pip install Django
# 解决CORS问题
pip install django-cors-headers
# ssh连接池
pip install paramiko
```

项目启动
```
cd 项目目录
python manage.py runserver 0.0.0.0:8000
```

或者挂载到后台执行：
```
nohup python manage.py runserver 0.0.0.0:8000 > server_log.log 2>&1 &
```

lsof -i :8000