#!/bin/bash
cd "$(dirname "$0")"

# Ưu tiên Python có Tk >= 8.6 (python.org / Homebrew).
# Tk 8.5 của hệ thống KHÔNG vẽ được chữ trên macOS mới
# (ô soạn thảo và các nhãn trắng trơn, chỉ nút bấm hiện).
pick_python() {
  local first=""
  for c in "/opt/homebrew/opt/python@3.12/bin/python3.12" \
           "/opt/homebrew/bin/python3" "/usr/local/bin/python3" \
           "/Library/Frameworks/Python.framework/Versions/Current/bin/python3" \
           "python3.13" "python3.12" "python3.11" "python3"; do
    command -v "$c" >/dev/null 2>&1 || continue
    local v
    v=$("$c" -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null) || continue
    [ -z "$first" ] && first="$c"
    if [ "$v" != "8.5" ]; then echo "$c"; return 0; fi
  done
  echo "${first:-python3}"
}

PY=$(pick_python)
TKV=$("$PY" -c "import tkinter; print(tkinter.TkVersion)" 2>/dev/null)
echo "==> Chạy bằng: $PY (Tk $TKV)"
if [ "$TKV" = "8.5" ]; then
  echo "⚠️  Tk 8.5 hệ thống KHÔNG hiển thị chữ trên macOS này."
  echo "    Fix triệt để:  brew install python@3.12"
  echo "    rồi chạy lại:  /opt/homebrew/bin/python3 auto_typer.py"
fi
"$PY" auto_typer.py
