# 中间件实现与验证

- 日期：2026-11-03
- 范围：Redis、RabbitMQ、Elasticsearch

## 一、实现位置

### Redis 缓存

- `CatalogCache.java`
- 本地缓存 + Redis 两级缓存
- 分类和商品详情读缓存
- `CacheHeaderAdvice.java` 返回 `X-Cache`：`miss` / `local` / `redis`

### RabbitMQ

- `ProductQueueConfig.java`
  - Exchange：`campus.product`
  - Queue：`campus.product.cache`
  - Routing key：`product.changed`
- `ProductEventPublisher.java`：商品变更发布事件
- `ProductCacheListener.java`：消费事件，失效缓存并同步 ES
- `RabbitConfig.java`：使用 JSON 消息转换器
- `application.yml`：连接、重试、不重新入队配置

### Elasticsearch

- `ProductSearchIndex.java`
  - 索引：`campus-products`
  - 启动时异步重建
  - 商品变更时增量同步
  - 关键词搜索失败自动降级 MySQL
- `CampusApi.java` `/api/products/search` 使用 ES，返回 `search_engine`

## 二、启动

```powershell
docker compose up -d rabbitmq elasticsearch
```

当前 Docker Hub 直连受限时，RabbitMQ 可使用 DaoCloud 镜像：

```powershell
docker pull docker.m.daocloud.io/library/rabbitmq:3-management
docker tag docker.m.daocloud.io/library/rabbitmq:3-management rabbitmq:3-management
```

Elasticsearch 镜像：

```powershell
docker pull docker.elastic.co/elasticsearch/elasticsearch:8.15.5
```

Java 服务仍需单独启动：

```powershell
cd server
java -jar target/market-server-0.1.0.jar
```

`docker-compose.yml` 当前只包含 Python 后端和前端，未包含 Java 8080 主服务。

## 三、已验证结果

### 基础状态

```text
RabbitMQ 5672 / 15672   运行
Elasticsearch 9200      运行
Redis 6379              运行
campus.product.cache    durable=true, consumers=1
campus-products         docs=45
```

### ES 搜索

```text
GET /api/products/search?q=手机
search_engine=elasticsearch
```

### ES 降级

停止 Elasticsearch 后：

```text
GET /api/products/search?q=手机
search_engine=mysql
```

重新启动 Elasticsearch 后恢复：

```text
search_engine=elasticsearch
```

### RabbitMQ 事件链路

通过商品编辑触发事件后：

- `cache_after=miss`
- ES 文档 version 从 3 增加到 4
- 队列消费完成，`messages=0, consumers=1`

### 缓存

```text
首次 /api/categories  -> X-Cache: miss
第二次                -> X-Cache: local
```

## 四、当前限制

- 已加入 `product_outbox`，RabbitMQ 发送失败会保留 pending 并定时重试
- ES 已加入定时检查，索引缺失时自动重建
- ES 搜索最多返回 50 个 ID，再交给 MySQL 过滤/排序
- Docker Compose 已加入 Java 服务定义，但尚未做容器化启动回归
- RabbitMQ、Elasticsearch 尚无自动化集成测试，当前为实际接口联调
