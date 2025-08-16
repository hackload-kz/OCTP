import importlib
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import NullPool
from sqlalchemy import create_engine

from app import database
from config import get_settings

# Ensure the root of the project is in the PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def import_submodules(directory, search="models"):
    """Import modules and packages that match the search criteria"""
    for root, dirs, files in os.walk(directory):
        for file_ in files:
            if not file_.endswith(".py"):
                continue
            if search in file_:
                module = root.replace(os.sep, ".") + "." + file_[:-3]
                importlib.import_module(module)
        for dir_ in dirs:
            if search in dir_:
                module = root.replace(os.sep, ".") + "." + dir_
                importlib.import_module(module)


import_submodules("app")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = database.Base.metadata


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    settings = get_settings()

    url = settings.POSTGRES_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    settings = get_settings()

    engine = create_engine(settings.POSTGRES_URL, poolclass=NullPool, echo=True)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()

    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
