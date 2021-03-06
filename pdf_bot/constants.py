import gettext

from telegram.ext import Filters

t = gettext.translation("pdf_bot", localedir="locale", languages=["en_GB"])
_ = t.gettext

TEXT_FILTER = Filters.text & ~Filters.command

# Bot constants
CHANNEL_NAME = "Mr. Developer"
SET_LANG = "set_lang"

# PDF file validation constants
PDF_OK = 0
PDF_INVALID_FORMAT = 1
PDF_TOO_LARGE = 2

# PDF file constants
WAIT_DOC_TASK = 0
WAIT_PHOTO_TASK = 1
WAIT_CROP_TYPE = 2
WAIT_CROP_PERCENT = 3
WAIT_CROP_OFFSET = 4
WAIT_DECRYPT_PW = 5
WAIT_ENCRYPT_PW = 6
WAIT_FILE_NAME = 7
WAIT_ROTATE_DEGREE = 8
WAIT_SPLIT_RANGE = 9
WAIT_SCALE_TYPE = 10
WAIT_SCALE_PERCENT = 11
WAIT_SCALE_DIMENSION = 12
WAIT_EXTRACT_PHOTO_TYPE = 13
WAIT_TO_PHOTO_TYPE = 14
WAIT_TEXT_TYPE = 15

# Keyboard constants
CANCEL = _("Cancel")
DONE = _("Done")
BACK = _("Back")
BY_PERCENT = _("By Percentage")
BY_SIZE = _("By Margin Size")
PREVIEW = _("Preview")
DECRYPT = _("Decrypt")
ENCRYPT = _("Encrypt")
EXTRACT_PHOTO = _("Extract Photos")
TO_PHOTO = _("To Photos")
ROTATE = _("Rotate")
SCALE = _("Scale")
SPLIT = _("Split")
BEAUTIFY = _("Beautify")
TO_PDF = _("To PDF")
RENAME = _("Rename")
CROP = _("Crop")
COMPRESSED = _("Compressed")
PHOTOS = _("Photos")
REMOVE_LAST = _("Remove Last File")
TO_DIMENSIONS = _("To Dimensions")
EXTRACT_TEXT = _("Extract Text")
TEXT_MESSAGE = _("Text Message")
TEXT_FILE = _("Text File")
OCR = "OCR"
COMPRESS = _("Compress")

# Rotation constants
ROTATE_90 = "90"
ROTATE_180 = "180"
ROTATE_270 = "270"

# User data constants
PDF_INFO = "pdf_info"

# Payment Constants
PAYMENT = "payment"
PAYMENT_PAYLOAD = "payment_payload"
CURRENCY = "INR"
PAYMENT_PARA = "payment_para"
THANKS = _("Say Thanks π (βΉ10)")
COFFEE = _("Coffee β (βΉ30)")
BOOK = _("Book π (βΉ50)")
MEAL = _("Meal π² (βΉ100)")
PAYMENT_DICT = {THANKS: 10, COFFEE: 30, BOOK: 50, MEAL: 100}
WAIT_PAYMENT = 0

# Datastore constants
USER = "User"
LANGUAGE = "language"

# Language constants
LANGUAGES = {
    "π¬π§ English (UK)": "en_GB",
    "πΊπΈ English (US)": "en_US",
    "π­π° ε»£ζ±θ©±": "zh_HK",
    "πΉπΌ ηΉι«δΈ­ζ": "zh_TW",
    "π¨π³ η?δ½δΈ­ζ": "zh_CN",
    "π?πΉ Italiano": "it_IT",
    "π¦πͺ Ω±ΩΩΨΉΩΨ±ΩΨ¨ΩΩΩΩΨ©β": "ar_SA",
    "π³π± Nederlands": "nl_NL",
    "π§π· PortuguΓͺs do Brasil": "pt_BR",
    "πͺπΈ espaΓ±ol": "es_ES",
    "πΉπ· TΓΌrkΓ§e": "tr_TR",
    "π?π± Χ’ΧΧ¨ΧΧͺ": "he_IL",
    "π·πΊ ΡΡΡΡΠΊΠΈΠΉ ΡΠ·ΡΠΊ": "ru_RU",
    "π«π· franΓ§ais": "fr_FR",
    "π±π° ΰ·ΰ·ΰΆΰ·ΰΆ½": "si_LK",
    "πΏπ¦ Afrikaans": "af_ZA",
    "catalΓ ": "ca_ES",
    "π¨πΏ ΔeΕ‘tina": "cs_CZ",
    "π©π° dansk": "da_DK",
    "π«π? suomen kieli": "fi_FI",
    "π©πͺ Deutsch": "de_DE",
    "π¬π· Ξ΅Ξ»Ξ»Ξ·Ξ½ΞΉΞΊΞ¬": "el_GR",
    "π­πΊ magyar nyelv": "hu_HU",
    "π―π΅ ζ₯ζ¬θͺ": "ja_JP",
    "π°π· νκ΅­μ΄": "ko_KR",
    "π³π΄ norsk": "no_NO",
    "π΅π± polski": "pl_PL",
    "π΅πΉ portuguΓͺs": "pt_PT",
    "π·π΄ Daco-Romanian": "ro_RO",
    # "π·πΈ ΡΡΠΏΡΠΊΠΈ ΡΠ΅Π·ΠΈΠΊ": "sr_SP",
    "πΈπͺ svenska": "sv_SE",
    "πΊπ¦ ΡΠΊΡΠ°ΡΠ½ΡΡΠΊΠ° ΠΌΠΎΠ²Π°": "uk_UA",
    "π»π³ TiαΊΏng Viα»t": "vi_VN",
    "π?π³ ΰ€Ήΰ€Ώΰ€¨ΰ₯ΰ€¦ΰ₯": "hi_IN",
}

LANGS_SHORT = {x.split("_")[0]: x for x in LANGUAGES.values()}
