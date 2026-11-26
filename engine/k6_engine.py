from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path

from config import K6_BIN, MAX_K6_DURATION, MAX_K6_RATE, MAX_K6_VUS


async def run_k6_test(url: str, vus: int = 2, duration: int = 10, rate: int = 1):
    if not 1 <= vus <= MAX_K6_VUS:
        raise ValueError("Nombre de VUs hors limites.")
    if not 1 <= duration <= MAX_K6_DURATION:
        raise ValueError("Durée hors limites.")
    if not 1 <= rate <= MAX_K6_RATE:
        raise ValueError("Débit hors limites.")

    script = f"""
import http from 'k6/http';
import {{ check }} from 'k6';

export const options = {{
  scenarios: {{
    controlled_load: {{
      executor: 'constant-arrival-rate',
      rate: {rate},
      timeUnit: '1s',
      duration: '{duration}s',
      preAllocatedVUs: {vus},
      maxVUs: {vus},
    }},
  }},
}};

const TARGET = {json.dumps(url)};

export default function () {{
  const response = http.get(TARGET, {{
    redirects: 0,
    timeout: '10s',
    tags: {{ test: 'stresslab' }},
  }});
  check(response, {{
    'HTTP response received': (r) => r.status > 0,
  }});
}}

export function handleSummary(data) {{
  return {{ 'summary.json': JSON.stringify(data, null, 2) }};
}}
"""

    with tempfile.TemporaryDirectory(prefix="stresslab-") as tmp:
        workdir = Path(tmp)
        script_path = workdir / "test.js"
        summary_path = workdir / "summary.json"
        script_path.write_text(script, encoding="utf-8")

        process = await asyncio.create_subprocess_exec(
            K6_BIN, "run", "--quiet", str(script_path),
            cwd=str(workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            stdout, _ = await asyncio.wait_for(
                process.communicate(), timeout=duration + 20
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise RuntimeError("Délai maximal du processus k6 dépassé.")

        output = stdout.decode(errors="replace")[-10000:]
        if process.returncode != 0:
            raise RuntimeError(f"k6 a échoué :\n{output}")
        if not summary_path.exists():
            raise RuntimeError("Rapport k6 introuvable.")

        return {
            "summary": json.loads(summary_path.read_text(encoding="utf-8")),
            "output": output,
        }
