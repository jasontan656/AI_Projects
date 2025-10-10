services:
  redis:
    container: "svc-redis"
    image: "redis:7"
    network: "ai_services_net"
    ports:
      host: 6379
      container: 6379
    healthcheck:
      command: "docker exec svc-redis redis-cli ping"
      expect: "PONG"
    connect_examples:
      - "redis-cli -h 127.0.0.1 -p 6379"

  mongodb:
    container: "svc-mongo"
    image: "mongo:7"
    network: "ai_services_net"
    ports:
      host: 27017
      container: 27017
    healthcheck:
      command: "docker exec svc-mongo mongosh --quiet --eval 'db.runCommand({ ping: 1 }).ok'"
      expect: 1
    connect_examples:
      - "mongosh \"mongodb://localhost:27017\""

  rabbitmq:
    container: "svc-rabbitmq"
    image: "rabbitmq:3-management"
    network: "ai_services_net"
    ports:
      amqp:
        host: 5672
        container: 5672
      management:
        host: 15672
        container: 15672
    credentials:
      username: "guest"
      password: "guest"
    management_ui: "http://localhost:15672"
    healthcheck:
      command: "docker exec svc-rabbitmq rabbitmq-diagnostics -q ping"
      expect: "Ping succeeded"
    connect_examples:
      - "amqp://guest:guest@localhost:5672"

  chromadb:
    container: "svc-chromadb"
    image: "chromadb/chroma:latest"
    network: "ai_services_net"
    ports:
      host: 8001
      container: 8001
    api:
      base_url: "http://localhost:8001"
      version_endpoint: "/api/v2/version"
      heartbeat_endpoint: "/api/v2/heartbeat"
    notes:
      - "v1 API 已弃用，请使用 /api/v2/*"
    healthcheck:
      endpoints:
        - "GET http://localhost:8001/api/v2/heartbeat"
        - "GET http://localhost:8001/api/v2/version"

docker:
  network: "ai_services_net"
  ps_example: "docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
  start_examples:
    - "docker start svc-redis svc-mongo svc-rabbitmq svc-chromadb"
  stop_examples:
    - "docker stop svc-redis svc-mongo svc-rabbitmq svc-chromadb"

说明:
  - "以上端口均为宿主机暴露端口；容器内部端口与之对应。"
  - "如需调整端口，更新映射（示例：-p <host_port>:<container_port>）并相应修改客户端连接。"
  - "RabbitMQ 管理界面默认账户为 guest/guest（仅本机访问时可用）；生产环境请自定义凭据。"
  - "ChromaDB 建议通过反向代理或网关统一外部路径风格，但不要修改服务内部 API 路径。"
  - "需要数据持久化时，请为各容器挂载卷（如 -v <host_path>:<container_path>）。"
