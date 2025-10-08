from src.config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, inspect, event
import traceback
import threading

# map connection id -> stacktrace where it was checked out
_checkout_stacks: dict = {}

# 创建数据库引擎（使用配置的连接池参数）
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
)


# Add listeners to log pool checkouts/checkins for debugging connection leaks
@event.listens_for(engine, "checkout")
def _checkout_listener(dbapi_con, con_record, con_proxy):
    try:
        cid = id(dbapi_con)

        # Extract a small stack snapshot (FrameSummary objects)
        frames = traceback.extract_stack(limit=12)

        # Decide whether to suppress immediate printing for noisy internal frames
        suppress_print = False
        for fr in frames:
            # if SQLAlchemy reflection or alembic/sys internals are present, suppress
            if 'sqlalchemy/engine/reflection.py' in (fr.filename or ''):
                suppress_print = True
                break

        # Store a compact stack string for later inspection
        try:
            stack_str = ''.join(traceback.format_list(frames))
        except Exception:
            stack_str = '<unavailable stack>'

        _checkout_stacks[cid] = (
            stack_str, threading.get_ident(), suppress_print)

        if not suppress_print:
            print(
                f"[DB POOL] checked out connection id={cid}, thread={threading.get_ident()}")
    except Exception:
        pass


@event.listens_for(engine, "checkin")
def _checkin_listener(dbapi_con, con_record):
    try:
        cid = id(dbapi_con)
        info = _checkout_stacks.pop(cid, None)
        if info:
            stack, thread_id, suppressed = info
            if suppressed:
                print(
                    f"[DB POOL] checked in connection id={cid}, thread={threading.get_ident()}, checked out by thread={thread_id} (checkout print suppressed - internal SQLAlchemy reflection)")
            else:
                print(
                    f"[DB POOL] checked in connection id={cid}, thread={threading.get_ident()}, checked out by thread={thread_id}\nSTACK AT CHECKOUT:\n{stack}")
        else:
            print(
                f"[DB POOL] checked in connection id={cid}, thread={threading.get_ident()}, no checkout record")
    except Exception:
        pass


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
        import src.models.site_info

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
        # record where the session was requested for debugging
        try:
            stack = ''.join(traceback.format_stack(limit=6))
            print(
                f"[DB SESSION] opened session id={id(db)} thread={threading.get_ident()}\nSTACK:\n{stack}")
        except Exception:
            pass

        yield db
    finally:
        try:
            print(
                f"[DB SESSION] closing session id={id(db)} thread={threading.get_ident()}")
        except Exception:
            pass
        db.close()
