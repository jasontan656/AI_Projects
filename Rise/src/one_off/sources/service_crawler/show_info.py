from pathlib import Path
import os

template_path = Path(os.environ.get("SERVICE_CRAWLER_YAML_TEMPLATE", str(Path(__file__).resolve().parent / "service_yaml_template.yaml")))
text = template_path.read_text(encoding="utf-8")
start = text.index("info_collect:")
end = text.index("acknowledgement_flags:")
print(text[start:end])
