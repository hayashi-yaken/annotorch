from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .services.exports import ExportService
from .services.projects import ProjectService
from .services.tasks import TaskService
from .storage.workspace import Workspace

DEFAULT_ROOT = Path.home() / ".annotorch"


def _parse_splits(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in text.split(","):
        name, _, value = part.partition("=")
        out[name.strip()] = float(value)
    return out


def _cmd_ls(args: argparse.Namespace) -> int:
    ws = Workspace(args.root)
    tasks_svc = TaskService(ws)
    for project in ProjectService(ws).list():
        print(f"{project.id}  {project.name}")
        for t in tasks_svc.list_tasks_with_progress(project.id):
            print(f"  {t.id}  {t.name}"
                  f"  {t.presentation.value}/{t.question.value}"
                  f"  {t.answered_units}/{t.total_units}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    svc = ExportService(Workspace(args.root))
    result = svc.export(
        args.project, args.task, Path(args.out),
        splits=_parse_splits(args.splits) if args.splits else None,
        seed=args.seed,
    )
    print(f"exported {result.num_rows} annotations to {result.output_dir}")
    if result.num_unanswered_units:
        print(f"warning: {result.num_unanswered_units} unanswered units were excluded")
    if result.num_skipped:
        print(f"warning: {result.num_skipped} skipped answers were excluded")
    print("\nload it with:\n"
          "  from annotorch.datasets import load\n"
          f"  ds = load({str(result.output_dir)!r}, split=\"train\")")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn

        from .server.app import create_app
    except ImportError:
        print(
            "error: server dependencies are not installed."
            " install with: pip install 'annotorch[server]'",
            file=sys.stderr,
        )
        return 1
    app = create_app(args.root)
    if not args.no_browser:
        import threading
        import webbrowser

        url = f"http://{args.host}:{args.port}"
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="annotorch")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ls = sub.add_parser("ls", help="list projects and tasks")
    p_ls.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_ls.set_defaults(func=_cmd_ls)

    p_export = sub.add_parser("export", help="export a task to a dataset directory")
    p_export.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_export.add_argument("--project", required=True)
    p_export.add_argument("--task", required=True)
    p_export.add_argument("--out", required=True)
    p_export.add_argument("--splits", default=None,
                          help='e.g. "train=0.8,test=0.2"')
    p_export.add_argument("--seed", type=int, default=0)
    p_export.set_defaults(func=_cmd_export)

    p_serve = sub.add_parser("serve", help="start the annotation server")
    p_serve.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    p_serve.add_argument("--no-browser", action="store_true")
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
