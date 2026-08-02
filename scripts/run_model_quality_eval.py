#!/Users/moonishaider/.hermes/hermes-agent/.venv/bin/python
"""Run the small Prompt 4 representative model evaluation."""

from __future__ import annotations

import argparse
import base64
from io import BytesIO
import json
import os
from pathlib import Path
import sys

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hermes_attention.config import ProjectPaths  # noqa: E402
from hermes_attention.model_quality import ModelQualityEvaluator, ROUTINE_TASKS  # noqa: E402
from hermes_attention.runtime_models import DirectModelClient  # noqa: E402
from hermes_attention.storage import Store  # noqa: E402


def image_data_url(text: str) -> str:
    image = Image.new("RGB", (1200, 440), "white")
    draw = ImageDraw.Draw(image)
    lines = []
    for paragraph in text.split(". "):
        while len(paragraph) > 92:
            cut = paragraph.rfind(" ", 0, 92)
            cut = cut if cut > 0 else 92
            lines.append(paragraph[:cut])
            paragraph = paragraph[cut:].lstrip()
        lines.append(paragraph)
    draw.multiline_text((30, 30), "\n".join(lines), fill="black", spacing=10)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-dir", type=Path, default=ROOT / "runtime-data/model-quality-private/prompt4")
    parser.add_argument("--summary", type=Path, default=ROOT / "runtime-data/model-quality-prompt4-summary.json")
    arguments = parser.parse_args()
    paths = ProjectPaths.discover(ROOT)
    images = {task.task_id: image_data_url(task.prompt) for task in ROUTINE_TASKS}
    with Store(paths.database) as store:
        result = ModelQualityEvaluator(DirectModelClient(paths.config_dir / "models.json", store), arguments.private_dir).run(routine_images=images)
    arguments.summary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(arguments.summary, 0o600)
    print(json.dumps({
        "rows": len(result["rows"]), "routine_comparison": result["routine_comparison"],
        "total_cost_usd": result["total_cost_usd"], "summary": str(arguments.summary),
        "private_content_printed": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
