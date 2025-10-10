Start Service

net start MongoDB

PS D:\mongodb\server\8.2\bin> 

.\mongod.exe `
  --dbpath  "D:\mongodb\data" `       # 告诉 mongod 用哪个数据目录（关键参数）
  --logpath "D:\mongodb\log\mongod.log" `  # 把日志写到这个文件
  --bind_ip 127.0.0.1 `               # 仅本机可连，安全起见
  --port    27017                     # 监听的端口（默认也是 27017）

  .\mongod.exe --config "D:\MongoDB\Server\8.2\bin\mongod.cfg"   # 读取配置并启动

  