import argparse
import json
import os

from sage_research.config import Config
from sage_research.orchestrator import Orchestrator


def cmd_list(data_dir: str):
    index_path = os.path.join(data_dir, "index.json")
    if not os.path.exists(index_path):
        print("文献库为空")
        return
    with open(index_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    if not entries:
        print("文献库为空")
        return
    for i, entry in enumerate(entries, 1):
        source = entry.get("source_type", "unknown")
        title = entry["title"]
        added = entry.get("added_at", "")[:10]
        print(f"  [{i}] {title}  ({source}) added_at: {added}")
    print(f"\n共 {len(entries)} 篇文献")


def cmd_add(config: Config, src: str, title: str, overwrite: bool):
    with Orchestrator(config) as orch:
        manager = orch.create_library_manager()
        manager.ingest(src, custom_title=title, overwrite=overwrite)


def cmd_delete(config: Config, title: str):
    with Orchestrator(config) as orch:
        manager = orch.create_library_manager()
        manager.delete_doc(title)
        print(f"已删除: {title}")


def main():
    parser = argparse.ArgumentParser(description="SAGE Research 文献库管理")
    subparsers = parser.add_subparsers(dest="action", required=True)

    subparsers.add_parser("list", help="列出所有文献")

    add_parser = subparsers.add_parser("add", help="添加文献")
    add_parser.add_argument("src", help="arXiv ID (如 2106.09685) 或本地文件路径 (.pdf/.md/.txt)")
    add_parser.add_argument("--title", default=None, help="自定义标题")
    add_parser.add_argument("--no-overwrite", action="store_true", help="同名文献已存在时跳过而非覆盖")

    delete_parser = subparsers.add_parser("delete", help="删除文献")
    delete_parser.add_argument("title", help="文献标题")

    args = parser.parse_args()
    config = Config()

    if args.action == "list":
        cmd_list(config.data_dir)
    elif args.action == "add":
        cmd_add(config, args.src, args.title, overwrite=not args.no_overwrite)
    elif args.action == "delete":
        cmd_delete(config, args.title)


if __name__ == "__main__":
    main()
