# 微信小程序

原生微信小程序 + TypeScript，目录：

```text
wx_client/
  miniprogram/
    app.ts
    app.json
    app.wxss
    pages/
    components/product-card/
    utils/
  project.config.json
```

## 启动

1. 启动后端：

```powershell
cd D:\aWusheng\SDproject
powershell -ExecutionPolicy Bypass -File .\scripts\start-mysql.ps1
docker compose up -d redis rabbitmq elasticsearch
```

另开终端：

```powershell
cd D:\aWusheng\SDproject\backend
python data_server.py
```

另开终端：

```powershell
cd D:\aWusheng\SDproject\server
java -jar target\market-server-0.1.0.jar
```

2. 打开微信开发者工具
3. 导入 `wx_client`
4. AppID 使用项目已配置的 AppID
5. 开发阶段关闭“合法域名校验”
6. 启动小程序

## 后端地址

开发默认：

```text
http://127.0.0.1:8080
```

真机调试改成电脑局域网 IP：

```text
http://192.168.x.x:8080
```

修改位置：

```text
miniprogram/utils/config.ts
```

真机不能使用 `127.0.0.1`。

## 页面

```text
首页
搜索（首页顶部入口）
商品详情
发布
我的发布
收藏（我的）
购物车
订单
消息
我的
账号设置
AI 购物助手
登录
注册
```

底部 tabBar：

```text
首页 / 发布 / 购物车 / 订单 / 我的
```

搜索不占 tabBar，收藏在“我的”里。

## 认证

- 登录：`POST /api/v1/auth/miniprogram/login`
- 刷新：`POST /api/v1/auth/miniprogram/refresh`
- access token 请求头：`Authorization: Bearer`
- refresh token 保存到 `wx.setStorageSync`
- 401 自动刷新并重放一次请求

## 发布

- 图片选择、预览、上传
- AI 识图填充名称、分类、成色和描述
- 同品类价格参考
- 商品名称、分类、成色、价格、描述、品牌、瑕疵、交易方式、交易地点
- 提交审核
- “我的发布”查看状态、编辑和删除
- 编辑复用同一个发布页

接口：

```text
POST /api/products/images
POST /api/products
PUT /api/products/{id}
DELETE /api/products/{id}
GET /api/v1/users/me/products
POST /api/ai/listing-recognize
GET /api/products/price-reference
```

## 主题

- 默认浅色，配色对齐 PC 端
- “我的”中手动切换深色模式
- 主题保存在本地 Storage
- 导航栏、tabBar 和页面背景同步切换
- 深色配色使用网页端暗色变量

## 当前范围

已实现：

- 登录/注册
- 首页、分页搜索、商品详情
- 收藏
- 发布闲置、AI 识图、价格参考
- 我的发布、编辑、删除
- 购物车
- 订单、模拟支付、取消订单、订单评价
- 消息
- 首页个性化推荐
- AI 购物助手
- AI 对话中的加购确认和卖家消息确认
- 我的统计、兴趣偏好、资料、修改密码、注销账号
- 深色模式

暂不包含：

- 管理员后台
- 邮箱验证/找回密码

## 验证

- 待微信开发者工具编译和真机验证
- 登录接口：错误验证码返回 422
- 刷新接口：无效 refresh token 返回 401
- 商品、收藏、购物车、订单、消息复用现有 Java 接口
- 发布依赖 Java 与 Python 数据服务同时启动
