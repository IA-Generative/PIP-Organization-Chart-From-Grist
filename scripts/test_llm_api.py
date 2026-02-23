#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from openai import OpenAI

DEFAULT_SCW_BASE_URL = "https://api.scaleway.ai/a9158aac-8404-46ea-8bf5-1ca048cd6ab4/v1"
DEFAULT_SCW_MODEL = "mistral-small-3.2-24b-instruct-2506"


def _extract_text(resp: Any) -> str:
    try:
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if not message:
            return ""
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    txt = item.get("text")
                    if isinstance(txt, str):
                        parts.append(txt)
                        continue
                    if item.get("type") == "output_text" and isinstance(item.get("value"), str):
                        parts.append(item.get("value"))
                        continue
                txt_attr = getattr(item, "text", None)
                if isinstance(txt_attr, str):
                    parts.append(txt_attr)
                    continue
                item_type = getattr(item, "type", None)
                item_value = getattr(item, "value", None)
                if item_type == "output_text" and isinstance(item_value, str):
                    parts.append(item_value)
            return "".join(parts).strip()
    except Exception:
        return ""
    return ""


def _extract_stream_text(stream: Any) -> str:
    chunks: list[str] = []
    for chunk in stream:
        try:
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if not delta:
                continue
            content = getattr(delta, "content", None)
            if isinstance(content, str):
                chunks.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, str):
                        chunks.append(item)
                    elif isinstance(item, dict):
                        txt = item.get("text")
                        if isinstance(txt, str):
                            chunks.append(txt)
        except Exception:
            continue
    return "".join(chunks).strip()


def _print_debug_response(prefix: str, resp: Any) -> None:
    try:
        payload = resp.model_dump(exclude_none=True)
    except Exception:
        try:
            payload = resp.to_dict()
        except Exception:
            payload = {"repr": repr(resp)}
    print(f"{prefix} raw:")
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:5000])


def _run_non_stream(client: OpenAI, *, model: str, prompt: str, max_tokens: int, debug: bool) -> tuple[bool, str]:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.0,
        stream=False,
        response_format={"type": "text"},
    )
    text = _extract_text(resp)
    if debug:
        finish = "n/a"
        try:
            if resp.choices:
                finish = str(getattr(resp.choices[0], "finish_reason", "n/a"))
        except Exception:
            pass
        print(f"[non-stream] finish_reason={finish} content_len={len(text)}")
        _print_debug_response("[non-stream]", resp)
    return bool(text), text


def _run_stream(client: OpenAI, *, model: str, prompt: str, max_tokens: int, debug: bool) -> tuple[bool, str]:
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.0,
        stream=True,
        response_format={"type": "text"},
    )
    text = _extract_stream_text(stream)
    if debug:
        print(f"[stream] content_len={len(text)}")
    return bool(text), text


def _run_test(mode: str, client: OpenAI, *, model: str, prompt: str, max_tokens: int, debug: bool) -> int:
    exit_code = 0

    if mode in {"non-stream", "both"}:
        print("== Test non-stream ==")
        ok, text = _run_non_stream(
            client, model=model, prompt=prompt, max_tokens=max_tokens, debug=debug
        )
        print(f"resultat: {'OK' if ok else 'VIDE'}")
        print(f"texte: {text if text else '<vide>'}")
        if not ok:
            exit_code = 1
        print()

    if mode in {"stream", "both"}:
        print("== Test stream ==")
        ok, text = _run_stream(client, model=model, prompt=prompt, max_tokens=max_tokens, debug=debug)
        print(f"resultat: {'OK' if ok else 'VIDE'}")
        print(f"texte: {text if text else '<vide>'}")
        if not ok:
            exit_code = max(exit_code, 2)
        print()

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description="Test rapide API LLM (Scaleway/OpenAI-compatible).")
    parser.add_argument(
        "--api-key",
        default=os.getenv("SCW_SECRET_KEY_LLM", ""),
        help="Cle API LLM (defaut: env SCW_SECRET_KEY_LLM).",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("SCW_LLM_BASE_URL", DEFAULT_SCW_BASE_URL),
        help="Endpoint base URL (defaut: env SCW_LLM_BASE_URL puis valeur projet).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("SCW_LLM_MODEL", DEFAULT_SCW_MODEL),
        help="Nom du modele (defaut: env SCW_LLM_MODEL puis valeur projet).",
    )
    parser.add_argument(
        "--mode",
        choices=["non-stream", "stream", "both"],
        default="both",
        help="Type de test a executer.",
    )
    parser.add_argument(
        "--prompt",
        default="Reponds exactement: ok",
        help="Prompt de test.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=64,
        help="max_tokens pour l'appel API.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Affiche des metadonnees de debug et une partie du payload brut.",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("ERREUR: api key absente. Definir SCW_SECRET_KEY_LLM ou passer --api-key.", file=sys.stderr)
        return 3

    print("Configuration:")
    print(f"- base_url: {args.base_url}")
    print(f"- model: {args.model}")
    print(f"- mode: {args.mode}")
    print()

    try:
        client = OpenAI(base_url=args.base_url, api_key=args.api_key)
        return _run_test(
            args.mode,
            client,
            model=args.model,
            prompt=args.prompt,
            max_tokens=args.max_tokens,
            debug=args.debug,
        )
    except Exception as exc:
        print(f"ERREUR appel API: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
