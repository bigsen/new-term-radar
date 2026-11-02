#!/usr/bin/env bash
set -euo pipefail

UPSTREAM_URL="${UPSTREAM_URL:-git@github.com:zhuyansen/new-term-radar.git}"
DO_PUSH=1
DO_REBASE=0

usage() {
  cat <<'USAGE'
用法:
  scripts/sync-upstream.sh [--no-push] [--rebase]

默认行为:
  1. 配置 upstream（如果还没有）
  2. fetch upstream / origin
  3. 更新本地 main：origin/main -> upstream/main
  4. push main 到你的 fork
  5. 回到当前分支。当前分支不会被自动改写

选项:
  --no-push    只更新本地，不 push origin
  --rebase     更新 main 后，把当前分支 rebase 到新的 main
  -h, --help   显示帮助
USAGE
}

for arg in "$@"; do
  case "$arg" in
    --no-push) DO_PUSH=0 ;;
    --rebase) DO_REBASE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数: $arg" >&2; usage; exit 2 ;;
  esac
done

die() {
  echo "错误: $*" >&2
  exit 1
}

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "当前目录不是 Git 仓库"

if ! git diff --quiet || ! git diff --cached --quiet; then
  die "工作区有未提交改动。先 commit 或 stash，再运行同步脚本。"
fi

if ! git remote get-url upstream >/dev/null 2>&1; then
  echo "添加 upstream: $UPSTREAM_URL"
  git remote add upstream "$UPSTREAM_URL"
fi

echo "获取源站和 fork..."
git fetch upstream --prune --tags
git fetch origin --prune

git rev-parse --verify upstream/main >/dev/null 2>&1 || die "找不到 upstream/main"
git show-ref --verify --quiet refs/heads/main || die "本地没有 main 分支"

current_branch="$(git symbolic-ref --quiet --short HEAD)" || die "当前处于 detached HEAD，先切回一个分支"
echo "当前分支: $current_branch"

echo "切换到 main..."
git switch main >/dev/null

if git rev-parse --verify origin/main >/dev/null 2>&1; then
  echo "同步 fork 的 origin/main..."
  git merge --ff-only origin/main >/dev/null || die "本地 main 与 origin/main 已分叉，需要手动处理"
fi

echo "合并源站 upstream/main..."
if ! git merge --no-edit upstream/main; then
  echo >&2
  echo "main 合并源站时出现冲突。解决冲突后运行:" >&2
  echo "  git add <冲突文件>" >&2
  echo "  git commit" >&2
  exit 1
fi

if [ "$DO_PUSH" -eq 1 ]; then
  echo "推送 main 到 origin..."
  git push origin main
else
  echo "已跳过 push。"
fi

if [ "$current_branch" != "main" ]; then
  echo "切回 $current_branch..."
  git switch "$current_branch" >/dev/null
fi

if [ "$DO_REBASE" -eq 1 ] && [ "$current_branch" != "main" ]; then
  echo "将 $current_branch rebase 到 main..."
  if ! git rebase main; then
    echo >&2
    echo "rebase 出现冲突。解决冲突后运行:" >&2
    echo "  git add <冲突文件>" >&2
    echo "  git rebase --continue" >&2
    echo "如果不想继续: git rebase --abort" >&2
    exit 1
  fi
fi

echo "完成。"
