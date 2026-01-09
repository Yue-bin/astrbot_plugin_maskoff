from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star, register
from astrbot.api import logger, AstrBotConfig


@register(
    "astrbot_plugin_maskoff",
    "识人术",
    "防止你的小llm因为别人把名字改成你的就认错人",
    "0.1.0",
)
class MyPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.id_map = self.parse_id_map_list(
            self.config.get("id_map_list", [])
        )  # 转dict，方便查询
        self.check_contain: bool = self.config.get("check_contain", False)
        self.warning_template: str = self.config.get("warning_template", "")
        self.notice_template: str = self.config.get("notice_template", "")

    async def initialize(self):
        logger.info("识人术，黑暗心理学，社交的手腕...")
        logger.info(f"当前加载的ID映射条目数: {len(self.id_map)}")

    # 用于解析配置文件中的ID映射列表
    @staticmethod
    def parse_id_map_list(
        id_map_list: list[dict[str, str]],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in id_map_list:
            nickname = item.get("nickname")
            user_id = item.get("user_id")
            if nickname and user_id:
                result[nickname] = user_id
        return result

    # 用于判断昵称与ID是否匹配，如果ID不在映射表中则默认匹配成功
    def is_id_match(self, nickname: str, user_id: str) -> bool:
        expected_id = self.id_map.get(nickname)
        if expected_id is None:
            return True
        return expected_id == user_id

    # 用于判断昵称是否包含映射表中的昵称，与此同时ID是否匹配
    # 返回值为 (是否包含且ID不匹配, 映射表中的昵称)
    def is_nickname_contain_and_id_mismatch(
        self, nickname: str, user_id: str
    ) -> tuple[bool, str]:
        for expected_nickname, expected_id in self.id_map.items():
            if expected_nickname in nickname and expected_id != user_id:
                return True, expected_nickname
        return False, ""

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
        elif self.check_contain:
            contain_mismatch, expected_nickname = (
                self.is_nickname_contain_and_id_mismatch(name, actual_id)
            )
            if contain_mismatch:
                logger.warning(
                    f"昵称包含映射表中的昵称但ID不匹配: 昵称={name}, ID={actual_id}, 期望ID={self.id_map.get(expected_nickname, '未知')}"
                )
                # 替换{actual_nickname}、{nickname} 、{actual_id} 和 {expected_id}
                notice_msg = (
                    self.config.get("notice_template", "")
                    .replace("{actual_nickname}", name)
                    .replace("{nickname}", expected_nickname)
                    .replace("{actual_id}", actual_id)
                    .replace(
                        "{expected_id}",
                        self.id_map.get(expected_nickname, "未知"),
                    )
                )
                # 给llm的请求中插入通知信息
                if notice_msg:
                    req.system_prompt += f"\n{notice_msg}"

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
