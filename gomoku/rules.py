"""规则配置模块：统一管理五子棋规则开关与参数"""
from dataclasses import dataclass


@dataclass
class RulesConfig:
    """五子棋规则配置

    Attributes:
        opening_mode: 开局模式，"specified"=指定开局，"free"=自由开局
        enable_forbidden: 是否启用黑棋禁手规则
        enable_three_hand_swap: 是否启用三手交换规则
        enable_fifth_n: 是否启用五手N打规则
        fifth_n_default: 五手N打默认数量
        allow_pass: 是否允许放弃行棋权
        pass_not_allowed_before_move: 前N着不允许放弃行棋权
    """
    opening_mode: str = "specified"
    enable_forbidden: bool = True
    enable_three_hand_swap: bool = True
    enable_fifth_n: bool = True
    fifth_n_default: int = 2
    allow_pass: bool = True
    pass_not_allowed_before_move: int = 5
