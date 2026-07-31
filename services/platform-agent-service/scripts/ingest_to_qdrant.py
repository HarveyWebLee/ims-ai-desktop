#!/usr/bin/env python3
"""
知识库（Qdrant）增删改查 CLI。

用法示例见 docs/architecture/05-qdrant-rag.md。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SERVICE_ROOT = Path(__file__).resolve().parent.parent
if str(_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SERVICE_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="平台知识库（Qdrant）增删改查",
    )
    parser.add_argument("--collection", default=None, help="覆盖配置中的 collection 名称")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出结果")

    # 增
    parser.add_argument(
        "--file", type=Path, action="append", default=[], help="入库单个文件（可重复）"
    )
    parser.add_argument(
        "--dir", type=Path, action="append", default=[], help="递归入库目录（可重复）"
    )
    parser.add_argument("--glob", default="**/*", help="目录扫描 glob，默认 **/*（任意层级）")
    parser.add_argument(
        "--ext",
        action="append",
        default=[],
        help="仅入库指定后缀，如 --ext .docx --ext .pdf（可重复）",
    )
    parser.add_argument(
        "--try-unknown",
        action="store_true",
        help="目录入库时对未列后缀也尝试文本解码（仍跳过明确二进制）",
    )
    parser.add_argument("--chunk-size", type=int, default=None, help="切块大小（字符）")
    parser.add_argument("--chunk-overlap", type=int, default=None, help="切块重叠（字符）")

    # 改
    parser.add_argument(
        "--replace-file",
        type=Path,
        action="append",
        default=[],
        help="更新：先按绝对路径删除旧 chunk，再重新入库（可重复）",
    )

    # 查
    parser.add_argument("--search", default=None, help="语义检索")
    parser.add_argument("--limit", type=int, default=5, help="检索/列表条数，默认 5")
    parser.add_argument("--count", action="store_true", help="输出当前 collection 点数")
    parser.add_argument(
        "--list",
        action="store_true",
        help="分页浏览（非语义）；可与 --source / --source-contains 联用",
    )
    parser.add_argument("--source", default=None, help="精确匹配 payload.source（list/delete）")
    parser.add_argument(
        "--source-contains",
        default=None,
        help="source 子串过滤（list/search）",
    )

    # 删
    parser.add_argument(
        "--delete-source",
        action="append",
        default=[],
        help="按 payload.source 精确删除（可重复；建议传文件绝对路径）",
    )
    parser.add_argument(
        "--delete-id",
        action="append",
        default=[],
        help="按 point id 删除（可重复）",
    )
    parser.add_argument(
        "--drop-collection",
        action="store_true",
        help="删除整个 collection（危险，需 --yes）",
    )
    parser.add_argument("--yes", action="store_true", help="确认危险操作")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    from app.config import settings
    from app.infrastructure.vector.client import probe_qdrant
    from app.infrastructure.vector.store import VectorStoreService

    probe = probe_qdrant()
    if not probe["ok"]:
        print(
            f"[错误] Qdrant 不可用: url={probe.get('url')!r} error={probe.get('error')}",
            file=sys.stderr,
        )
        print(
            "请先执行: bash scripts/up.sh（或 docker compose -f deploy/docker-compose.yml up -d），并确认 .env 中 QDRANT_URL=http://127.0.0.1:16333",
            file=sys.stderr,
        )
        return 1

    store = VectorStoreService(collection=args.collection)
    summary: dict[str, object] = {
        "collection": store.collection,
        "qdrant_url": settings.qdrant_url,
        "files": {},
        "dirs": {},
        "replaced": {},
        "deleted_sources": {},
        "deleted_ids": 0,
        "dropped": False,
        "count": None,
        "list": None,
        "search": None,
    }

    did_work = False

    # —— 删 ——
    if args.drop_collection:
        if not args.yes:
            print("删除整个 collection 需要同时传 --yes", file=sys.stderr)
            return 2
        summary["dropped"] = store.drop_collection()
        print(f"[删库] collection={store.collection} dropped={summary['dropped']}")
        did_work = True

    for src in args.delete_source:
        n = store.delete_by_source(src)
        summary["deleted_sources"][src] = n  # type: ignore[index]
        print(f"[删除] source={src!r} count={n}")
        did_work = True

    if args.delete_id:
        n = store.delete_by_ids(list(args.delete_id))
        summary["deleted_ids"] = n
        print(f"[删除] ids={len(args.delete_id)} deleted={n}")
        did_work = True

    # —— 增 ——
    for file_path in args.file:
        store.ensure_collection()
        count = store.ingest_file(
            file_path,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        summary["files"][str(file_path)] = count  # type: ignore[index]
        print(f"[入库] file={file_path} chunks={count}")
        did_work = True

    for dir_path in args.dir:
        store.ensure_collection()
        suffix_set = None
        if args.ext:
            suffix_set = {(e if e.startswith(".") else f".{e}").lower() for e in args.ext}
        result = store.ingest_directory(
            dir_path,
            glob=args.glob,
            suffixes=suffix_set,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            try_unknown=bool(args.try_unknown),
        )
        summary["dirs"][str(dir_path)] = result  # type: ignore[index]
        total = sum(result.values())
        print(f"[入库] dir={dir_path} files={len(result)} chunks={total}")
        did_work = True

    # —— 改 ——
    for file_path in args.replace_file:
        store.ensure_collection()
        count = store.replace_file(
            file_path,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        summary["replaced"][str(file_path)] = count  # type: ignore[index]
        print(f"[替换] file={file_path} chunks={count}")
        did_work = True

    # —— 查 ——
    if args.count:
        n = store.count()
        summary["count"] = n
        print(f"[计数] collection={store.collection} points={n}")
        did_work = True

    if args.list:
        hits, _next = store.scroll_points(
            limit=args.limit,
            source_equals=args.source,
            source_contains=args.source_contains,
        )
        summary["list"] = [
            {
                "id": h.id,
                "source": h.payload.get("source"),
                "chunk_index": h.payload.get("chunk_index"),
                "text": h.text[:300],
            }
            for h in hits
        ]
        if not args.json:
            print(f"\n[列表] hits={len(hits)}")
            for i, hit in enumerate(hits, start=1):
                src = hit.payload.get("source") or ""
                preview = hit.text.replace("\n", " ")[:120]
                print(f"  {i}. id={hit.id} source={src}")
                print(f"     {preview}")
        did_work = True

    if args.search:
        hits = store.similarity_search(
            args.search,
            limit=args.limit,
            source_contains=args.source_contains,
        )
        summary["search"] = [
            {
                "id": h.id,
                "score": h.score,
                "text": h.text[:500],
                "source": h.payload.get("source"),
            }
            for h in hits
        ]
        if not args.json:
            print(f"\n[检索] query={args.search!r} hits={len(hits)}")
            for i, hit in enumerate(hits, start=1):
                src = hit.payload.get("source") or ""
                preview = hit.text.replace("\n", " ")[:160]
                print(f"  {i}. score={hit.score:.4f} source={src}")
                print(f"     {preview}")
        did_work = True

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    elif not did_work:
        print("未指定操作，请查看 --help", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
