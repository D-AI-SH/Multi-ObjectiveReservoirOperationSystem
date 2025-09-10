from __future__ import annotations

from typing import Any


class AIConfigMixin:
    data_manager: Any

    def open_ai_config(self) -> None:
        from ..ai_config_dialog import AIConfigDialog

        current_config = {
            "ai_enabled": self.data_manager.ai_enabled,
            "api_key": getattr(self.data_manager, "ai_api_key", ""),
            "api_url": getattr(
                self.data_manager, "ai_api_url", "https://api.ai-assistant.com/v1/chat/completions"
            ),
            "model": getattr(self.data_manager, "ai_model", "gpt-3.5-turbo"),
        }

        dialog = AIConfigDialog(self, current_config)
        dialog.config_changed.connect(self.on_ai_config_changed)  # type: ignore[attr-defined]

        if dialog.exec() == AIConfigDialog.DialogCode.Accepted:
            print("AI配置已更新")

    def on_ai_config_changed(self, config: dict) -> None:
        self.data_manager.ai_enabled = config.get("ai_enabled", False)
        self.data_manager.ai_api_key = config.get("api_key", "")
        self.data_manager.ai_api_url = config.get("api_url", "")
        self.data_manager.ai_model = config.get("model", "gpt-3.5-turbo")

        if hasattr(self.data_manager, "smart_processor"):
            self.data_manager.smart_processor.ai_enabled = config.get("ai_enabled", False)

        print(f"AI配置已更新: 启用={config.get('ai_enabled')}")


