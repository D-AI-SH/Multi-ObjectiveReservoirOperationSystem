from pathlib import Path


def alias_from_folder(folder_path: str) -> str:
    base = Path(folder_path).name
    return base.replace(" ", "_").replace("-", "_")


def db_table_name(alias: str, file_name: str) -> str:
    stem = Path(file_name).stem.replace(" ", "_").replace("-", "_")
    return f"{alias}_{stem}"


BASE_DIR = Path("data/reservoirs")


