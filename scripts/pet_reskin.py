#!/usr/bin/env python3
"""pet_reskin.py — One-command orchestrator for pet-reskin."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(label: str, cmd: list[str]) -> None:
    print(f"\n== {label} ==")
    print(" ".join(str(part) for part in cmd))
    completed = subprocess.run(cmd)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate, validate, and install a canvas-pet reskin")
    parser.add_argument("--plan", required=True, type=Path, help="Path to plan.json")
    parser.add_argument("--target", required=True, type=Path, help="canvas-pet project root")
    parser.add_argument("--out", required=True, type=Path, help="Output directory")
    parser.add_argument("--model", help="Gemini image model ID")
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", help="Repair one or more sprites by frame/file/role")
    cloud_group = parser.add_mutually_exclusive_group()
    cloud_group.add_argument("--with-cloud", action="store_true", help="Force generation of optional cloud.png")
    cloud_group.add_argument("--without-cloud", action="store_true", help="Force skipping optional cloud.png")
    args = parser.parse_args()

    py = sys.executable
    run_step("preflight", [py, str(SCRIPT_DIR / "check_env.py"), "--target", str(args.target)])

    generate_cmd = [py, str(SCRIPT_DIR / "generate_sprites.py"), "--skill-plan", str(args.plan), "--out", str(args.out)]
    if args.model:
        generate_cmd += ["--model", args.model]
    if args.allow_partial:
        generate_cmd.append("--allow-partial")
    if args.dry_run:
        generate_cmd.append("--dry-run")
    if args.only:
        generate_cmd += ["--only", args.only]
    if args.with_cloud:
        generate_cmd.append("--with-cloud")
    if args.without_cloud:
        generate_cmd.append("--without-cloud")
    run_step("generate", generate_cmd)

    if args.dry_run or args.only:
        print("\nGeneration dry-run or repair-only mode completed; install step skipped.")
        return

    manifest = args.out / "manifest.json"
    run_step("validate sprites", [py, str(SCRIPT_DIR / "validate_output.py"), "--manifest", str(manifest), "--sprites", str(args.out)])

    apply_cmd = [py, str(SCRIPT_DIR / "apply_config.py"), "--manifest", str(manifest), "--sprites", str(args.out), "--target", str(args.target)]
    if args.allow_partial:
        apply_cmd.append("--allow-partial")
    run_step("install", apply_cmd)

    run_step("validate install", [py, str(SCRIPT_DIR / "validate_output.py"), "--manifest", str(manifest), "--sprites", str(args.out), "--target", str(args.target), "--report", str(args.out / "validation-report.json")])
    print(f"\nDone. Validation report: {args.out / 'validation-report.json'}")


if __name__ == "__main__":
    main()
