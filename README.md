# Motion Vote Backend

辩论活动实时投票互动系统后端 API

## 项目概述

本项目为辩论赛事提供完整的实时投票互动解决方案，支持活动组织者高效管理辩论赛事，为现场观众提供便捷的投票互动体验，并通过大屏实时展示投票数据。

## 核心功能模块

- **用户管理**：注册登录、权限控制
- **活动管理**：创建活动、协作管理、参与者管理
- **辩题管理**：创建辩题、状态控制、实时切换
- **投票系统**：参与者入场、投票改票、结果锁定
- **大屏展示**：实时数据展示、主题控制
- **数据统计**：实时看板、活动报告、数据导出

## 技术栈

- **Web 框架**: FastAPI
- **数据库**: PostgreSQL + SQLAlchemy
- **缓存**: Redis
- **认证**: JWT
- **任务队列**: Celery
- **实时通信**: WebSockets
- **文档**: OpenAPI/Swagger

## 项目结构

```text
backend/
├── src/                        # 源代码目录
│   ├── api/                    # API路由
│   │   ├── v1/                # API版本1
│   │   │   ├── endpoints/     # 端点实现
│   │   │   └── router.py      # 路由配置
│   │   └── dependencies.py    # 依赖注入
│   ├── core/                   # 核心模块
│   │   ├── auth.py            # 认证相关
│   │   ├── database.py        # 数据库配置
│   │   └── exceptions.py      # 异常处理
│   ├── models/                 # 数据模型
│   │   ├── user.py
│   │   ├── activity.py
│   │   ├── debate.py
│   │   └── vote.py
│   ├── schemas/                # Pydantic模式
│   │   ├── user.py
│   │   ├── activity.py
│   │   ├── debate.py
│   │   └── vote.py
│   ├── services/               # 业务逻辑服务
│   │   ├── auth_service.py
│   │   └── user_service.py
│   ├── config.py              # 配置文件
│   └── main.py               # 应用入口
├── tests/                     # 测试文件
├── requirements.txt           # 依赖列表
├── .env.example              # 环境变量示例
└── run.py                    # 启动脚本
```

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 数据库配置

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置数据库连接
DATABASE_URL=postgresql://username:password@localhost:5432/motionvote
```

### 3. 初始化数据库

```bash
# 创建数据库表
python init_db.py
```

### 4. 启动应用

```bash
# 开发模式启动
python run.py

# 或使用uvicorn直接启动
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

- Swagger UI: <http://localhost:8000/api/docs>
- ReDoc: <http://localhost:8000/api/redoc>
- OpenAPI JSON: <http://localhost:8000/api/openapi.json>

## 开发指南

### API 设计规范

- 遵循 RESTful API 设计原则
- 使用标准 HTTP 状态码
- 统一的响应格式
- 完整的请求验证和错误处理

### 数据库设计

- 使用 SQLAlchemy ORM
- 遵循外键约束和索引优化
- 直接创建数据库表结构

### 认证授权

- JWT Token 认证
- 基于角色的权限控制
- 参与者通过活动 ID+编号验证

### 测试

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=src

# 运行特定测试文件
pytest tests/test_auth.py
```

## 部署

### 使用 Docker

```bash
# 构建镜像
docker build -t motion-vote-backend .

# 运行容器
docker run -d -p 8000:8000 --env-file .env motion-vote-backend
```

### 使用 docker-compose

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 Apache 2.0 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

## 联系方式

- 项目维护者: Computer Psycho Union
- 邮箱: <computerpsychounion@nottingham.edu.cn>
