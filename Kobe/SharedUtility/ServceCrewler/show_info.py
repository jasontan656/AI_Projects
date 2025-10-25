from pathlib import Path
text = Path(r"D:/AI_Projects/TelegramChatHistory/Workspace/VBcombined/service_yaml_template.yaml").read_text(encoding="utf-8")
start = text.index("info_collect:")
end = text.index("acknowledgement_flags:")
print(text[start:end])
