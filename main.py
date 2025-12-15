from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig


@register(
    "astrbot_plugin_maskoff",
    "识人术",
    "防止你的小llm因为别人把名字改成你的就认错人",
    "0.0.1",
)
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.id_map = self.parse_id_map_list(self.config.get("id_map_list", []))

    async def initialize(self):
        logger.info("识人术，黑暗心理学，社交的手腕...")
        logger.info(
            f"当前加载的ID映射条目数: {len(self.config.get('id_map_list', []))}"
        )

    # 用于解析配置文件中的ID映射列表
    @staticmethod
    def parse_id_map_list(id_map_list) -> dict[str, str]:
        def validate_entry(raw: str) -> tuple[str, str] | None:
            try:
                left, right = raw.split(",", maxsplit=1)
            except ValueError:
                logger.warning(f"无效的ID映射条目: {raw!r}")
                return None
            return left, right

        result: dict[str, str] = {}
        for item in id_map_list:
            entry = validate_entry(item)
            if entry is not None:
                nickname, user_id = entry
                result[nickname.strip()] = user_id.strip()
        return result

    # 用于判断昵称与ID是否匹配，如果ID不在映射表中则默认匹配成功
    def is_id_match(self, nickname: str, user_id: str) -> bool:
        expected_id = self.id_map.get(nickname)
        if expected_id is None:
            return True
        return expected_id == user_id

    # 检查每条信息的昵称和ID，并在发送给llm前插入警告
    @filter.on_llm_request()
    async def check_id(self, event: AstrMessageEvent, req: ProviderRequest):
        name = event.get_sender_name().strip()
        actual_id = event.get_sender_id()
        if not self.is_id_match(name, actual_id):
            logger.warning(
                f"昵称与ID不匹配: 昵称={name}, ID={actual_id}, 期望ID={self.id_map.get(name, '未知')}"
            )
            # 替换{nickname} 、{actual_id} 和 {expected_id}
            warning_msg = (
                self.config.get("warning_template", "")
                .replace("{nickname}", name)
                .replace("{actual_id}", actual_id)
                .replace("{expected_id}", self.id_map.get(name, "未知"))
            )
            # 给llm的请求中插入警告信息，参考astrbot_plugin_favourpro
            if warning_msg:
                req.system_prompt += f"\n{warning_msg}"

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
