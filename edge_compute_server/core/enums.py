from enum import Enum, IntEnum


class Language(str, Enum):
    ENGLISH = "en"
    KOREAN = "ko"
    JAPANESE = "ja"
    CHINESE = "zh"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"


class Role(str, Enum):
    CHRISTIAN = "christian"
    CASUAL = "casual"
    MULTILINGUAL = "multilingual"
    CAL_TRACKER = "cal_tracker"
    ROMANTIC = "romantic"
    ASSISTANT = "assistant"
    WORKOUT = "workout"
    SECRETS = "secrets"


class Tone(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"


class IntimacyLevel(IntEnum):
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4
    LEVEL_5 = 5
    LEVEL_6 = 6
    LEVEL_7 = 7
    LEVEL_8 = 8
    LEVEL_9 = 9
    LEVEL_10 = 10
