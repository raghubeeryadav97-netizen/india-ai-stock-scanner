"""Deploy India AI Stock Scanner to Hugging Face Spaces (permanent free hosting)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

APP_DIR = Path(__file__).parent
SPACE_ID = os.environ.get("HF_SPACE_ID", "india-ai-stock-scanner")
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()

FILES = [
    "streamlit_app.py",
    "india_ai_stock_scanner_streamlit.py",
    "requirements.txt",
    ".streamlit/config.toml",
    "artifacts/saved_ai_stock_analysis.json",
]

README = """---
title: India AI Stock Scanner
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.30.0
app_file: streamlit_app.py
pinned: false
license: mit
---

# India AI Stock Scanner

AI-powered Indian equity scanner. Paste JSON from sidebar to load analysis.

**Disclaimer:** Educational research only. Not investment advice.
"""


def main() -> int:
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN not set.")
        print("Steps:")
        print("1) Create free account: https://huggingface.co/join")
        print("2) Create token: https://huggingface.co/settings/tokens (Write access)")
        print("3) Run in PowerShell:")
        print('   $env:HF_TOKEN="hf_xxxx"')
        print(f'   $env:HF_SPACE_ID="{SPACE_ID}"')
        print("   python deploy_permanent_hf.py")
        return 1

    from huggingface_hub import HfApi, create_repo

    api = HfApi(token=HF_TOKEN)
    user = api.whoami()["name"]
    repo_id = f"{user}/{SPACE_ID}"
    print(f"Deploying to: https://huggingface.co/spaces/{repo_id}")

    create_repo(
        repo_id=repo_id,
        repo_type="space",
        space_sdk="streamlit",
        private=False,
        exist_ok=True,
        token=HF_TOKEN,
    )

    upload_paths: list[tuple[str, str]] = [("README.md", README)]
    for rel in FILES:
        src = APP_DIR / rel
        if not src.exists():
            print(f"Missing file: {rel}")
            return 2
        upload_paths.append((rel.replace("\\", "/"), src.read_text(encoding="utf-8") if rel.endswith((".py", ".txt", ".toml", ".json", ".md")) else None))

    for path, content in upload_paths:
        if content is not None:
            api.upload_file(
                path_or_fileobj=content.encode("utf-8"),
                path_in_repo=path,
                repo_id=repo_id,
                repo_type="space",
                token=HF_TOKEN,
                commit_message=f"Update {path}",
            )
            print(f"Uploaded: {path}")

    print("\nSUCCESS! Permanent URL:")
    print(f"https://{user}-{SPACE_ID}.hf.space")
    print(f"https://huggingface.co/spaces/{repo_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())