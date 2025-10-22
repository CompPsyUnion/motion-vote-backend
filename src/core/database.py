from sqlalchemy import create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.config import settings

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,          # 连接池预检查，防止使用已断开的连接
    pool_recycle=300,             # 每5分钟回收连接
    pool_size=50,                 # 连接池大小从5增加到20
    max_overflow=60,              # 最大溢出连接数从10增加到30
    pool_timeout=60,              # 连接超时时间从30秒增加到60秒
    echo_pool=False,              # 生产环境关闭连接池日志
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()


def init_database():
    """初始化数据库，如果表不存在则自动创建，如果表缺少列则添加"""
    try:
        # 检查数据库连接
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        # 导入所有模型以确保它们被注册到Base.metadata
        import src.models.activity
        import src.models.debate
        import src.models.site_info
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
            print("✅ 数据库表已存在，正在检查表结构...")

            # 检查现有表的列是否完整
            from sqlalchemy import text
            for table_name in expected_tables:
                if table_name in existing_tables:
                    existing_columns = {col['name']
                                        for col in inspector.get_columns(table_name)}
                    expected_columns = {
                        col.name for col in Base.metadata.tables[table_name].columns}

                    missing_columns = expected_columns - existing_columns

                    if missing_columns:
                        print(f"表 {table_name} 缺少列: {missing_columns}")
                        print("正在添加缺失的列...")

                        # 为每个缺失的列添加 ALTER TABLE 语句
                        for col_name in missing_columns:
                            col = Base.metadata.tables[table_name].columns[col_name]
                            # 构建 ALTER TABLE 语句
                            col_type = str(col.type).upper()
                            nullable = "NULL" if col.nullable else "NOT NULL"
                            default = f"DEFAULT {col.default.arg}" if col.default else ""

                            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}".strip(
                            )

                            try:
                                with engine.connect() as conn:
                                    conn.execute(text(alter_sql))
                                    conn.commit()
                                print(f"✅ 已添加列 {table_name}.{col_name}")
                            except Exception as e:
                                print(f"❌ 添加列 {table_name}.{col_name} 失败: {e}")

            print("✅ 数据库表结构检查完成")

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
