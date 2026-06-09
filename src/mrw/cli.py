"""CLI 入口"""

import argparse
import sys

from .pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="AI 辅助市场研究工作流")
    subparsers = parser.add_subparsers(dest="command")

    # run 命令
    run_parser = subparsers.add_parser("run", help="运行完整 Pipeline")
    run_parser.add_argument("--brief", required=True, help="Brief YAML 路径")
    run_parser.add_argument("--data", required=True, help="数据文件路径")
    run_parser.add_argument("--output", default="outputs", help="输出目录")

    args = parser.parse_args()

    if args.command == "run":
        result = run_pipeline(args.brief, args.data, args.output)
        print("\n=== Pipeline 完成 ===")
        print(f"洞察数量: {result['insights_count']}")
        print(f"校验通过率: {result['validation_summary']['pass_rate']:.0%}")
        print(f"报告路径: {result['report_path']}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
