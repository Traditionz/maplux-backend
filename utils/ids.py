from snowflake import SnowflakeGenerator

_id_generator = SnowflakeGenerator(42)


def generate_id() -> int:
    return next(_id_generator)
