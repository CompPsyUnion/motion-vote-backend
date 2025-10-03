from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def init_database():
    """初始化数据库，如果表不存在则自动创建"""
    try:
        # 检查数据库连接
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # 导入所有模型以确保它们被注册到Base.metadata
        import src.models.activity
        import src.models.debate
        import src.models.user
        import src.models.vote

        # 获取所有应该存在的表
        expected_tables = list(Base.metadata.tables.keys())

        # 检查是否有缺失的表
        missing_tables = [
            table for table in expected_tables if table not in existing_tables]

        if missing_tables:
            print(f"发现缺失的数据库表: {missing_tables}")
            print("正在创建数据库表...")

            # 创建所有表
            Base.metadata.create_all(bind=engine)

            print("✅ 数据库表创建成功！")
            print(f"📋 已创建的表: {expected_tables}")
        else:
            print("✅ 数据库表已存在，无需创建")

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        raise


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
