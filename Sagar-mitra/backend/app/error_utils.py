"""
Sagar Mitra / ORCA - Error Sanitization
===========================================
Every raw exception from a Gemini call (429 quota, 503 overloaded, network
errors) used to get stringified straight into agent output and from there
into the synthesized advisory -- so a quota hit showed up in the chat UI as
a raw {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED', ...}} JSON
blob. This module gives every call site one place to turn that into a
short, honest, user-safe notice instead -- localized for the languages this
platform explicitly targets, so even a degraded response doesn't silently
drop back to English-only.
"""
import re

_QUOTA_OR_UNAVAILABLE_PATTERNS = (
    "429", "resource_exhausted", "quota", "rate limit",
    "503", "unavailable", "high demand", "overloaded",
)


def is_quota_or_unavailable_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(p in msg for p in _QUOTA_OR_UNAVAILABLE_PATTERNS)


# Short, plain-language notices for the languages named in the ORCA brief.
# These are static translations of ONE sentence, not a substitute for real
# LLM translation of the underlying data -- but they mean a quota outage
# never silently reverts a non-English conversation to raw English text.
BUSY_NOTICE = {
    "English": "ORCA's AI summarizer is temporarily busy (high demand). Showing the raw data ORCA's sensors already collected below.",
    "Hindi": "ORCA की AI सेवा अभी अधिक मांग के कारण व्यस्त है। नीचे ORCA के सेंसर से मिला सीधा डेटा दिखाया जा रहा है।",
    "Marathi": "ORCA ची AI सेवा सध्या जास्त मागणीमुळे व्यस्त आहे. खाली ORCA च्या सेन्सर्सनी गोळा केलेला थेट डेटा दाखवला आहे.",
    "Gujarati": "ORCA ની AI સેવા હાલમાં વધુ માંગને કારણે વ્યસ્ત છે. નીચે ORCA ના સેન્સરે એકત્રિત કરેલો સીધો ડેટા બતાવવામાં આવ્યો છે.",
    "Kannada": "ORCA ದ AI ಸೇವೆ ಸದ್ಯಕ್ಕೆ ಹೆಚ್ಚಿನ ಬೇಡಿಕೆಯಿಂದಾಗಿ ಬ್ಯುಸಿಯಾಗಿದೆ. ಕೆಳಗೆ ORCA ದ ಸಂವೇದಕಗಳು ಸಂಗ್ರಹಿಸಿದ ನೇರ ಡೇಟಾ ತೋರಿಸಲಾಗಿದೆ.",
    "Tamil": "ORCA இன் AI சேவை அதிக தேவை காரணமாக தற்போது பிஸியாக உள்ளது. கீழே ORCA இன் சென்சார்கள் சேகரித்த நேரடி தரவு காட்டப்பட்டுள்ளது.",
    "Telugu": "ORCA యొక్క AI సేవ ప్రస్తుతం ఎక్కువ డిమాండ్ కారణంగా బిజీగా ఉంది. దిగువన ORCA సెన్సార్లు సేకరించిన ప్రత్యక్ష డేటా చూపబడింది.",
    "Malayalam": "ORCA യുടെ AI സേവനം ഇപ്പോൾ ഉയർന്ന ഡിമാൻഡ് കാരണം തിരക്കിലാണ്. താഴെ ORCA യുടെ സെൻസറുകൾ ശേഖരിച്ച നേരിട്ടുള്ള ഡാറ്റ കാണിച്ചിരിക്കുന്നു.",
    "Bengali": "ORCA-র AI পরিষেবা বর্তমানে অত্যধিক চাহিদার কারণে ব্যস্ত। নিচে ORCA-র সেন্সর সংগ্রহ করা সরাসরি তথ্য দেখানো হয়েছে।",
    "Punjabi": "ORCA ਦੀ AI ਸੇਵਾ ਇਸ ਵੇਲੇ ਵਧੇਰੇ ਮੰਗ ਕਾਰਨ ਰੁੱਝੀ ਹੋਈ ਹੈ। ਹੇਠਾਂ ORCA ਦੇ ਸੈਂਸਰਾਂ ਦੁਆਰਾ ਇਕੱਠਾ ਕੀਤਾ ਸਿੱਧਾ ਡਾਟਾ ਦਿਖਾਇਆ ਗਿਆ ਹੈ।",
    "Odia": "ORCA ର AI ସେବା ବର୍ତ୍ତମାନ ଅଧିକ ଚାହିଦା କାରଣରୁ ବ୍ୟସ୍ତ ଅଛି। ତଳେ ORCA ର ସେନ୍ସର ସଂଗ୍ରହ କରିଥିବା ସିଧାସଳଖ ତଥ୍ୟ ଦେଖାଯାଇଛି।",
}

GENERIC_ERROR_NOTICE = {
    "English": "ORCA had trouble processing part of this request.",
    "Hindi": "ORCA को इस अनुरोध के एक हिस्से को संसाधित करने में समस्या हुई।",
    "Marathi": "ORCA ला या विनंतीचा काही भाग हाताळताना अडचण आली.",
    "Bengali": "ORCA এই অনুরোধের একটি অংশ প্রক্রিয়া করতে সমস্যায় পড়েছে।",
    "Kannada": "ಈ ವಿನಂತಿಯ ಒಂದು ಭಾಗವನ್ನು ಪ್ರಕ್ರಿಯೆಗೊಳಿಸುವಲ್ಲಿ ORCA ಗೆ ತೊಂದರೆಯಾಯಿತು.",
    "Punjabi": "ORCA ਨੂੰ ਇਸ ਬੇਨਤੀ ਦੇ ਇੱਕ ਹਿੱਸੇ ਦੀ ਪ੍ਰਕਿਰਿਆ ਕਰਨ ਵਿੱਚ ਮੁਸ਼ਕਲ ਆਈ।",
    "Odia": "ORCA ଏହି ଅନୁରୋଧର ଏକ ଅଂଶ ପ୍ରକ୍ରିୟା କରିବାରେ ଅସୁବିଧାର ସମ୍ମୁଖୀନ ହେଲା।",
}


def busy_notice(language: str = "English") -> str:
    return BUSY_NOTICE.get(language, BUSY_NOTICE["English"])


def generic_error_notice(language: str = "English") -> str:
    return GENERIC_ERROR_NOTICE.get(language, GENERIC_ERROR_NOTICE["English"])


def safe_error_text(e: Exception, language: str = "English") -> str:
    """
    Never returns a raw exception string (which may contain a full Gemini
    JSON error body) -- always a short, localized, human-safe notice.
    """
    return busy_notice(language) if is_quota_or_unavailable_error(e) else generic_error_notice(language)


def strip_raw_error_artifacts(text: str) -> str:
    """
    Defense in depth: if a raw exception string somehow still made it into a
    piece of text (e.g. a third-party call this module doesn't wrap yet),
    strip the recognizable Gemini error JSON shape rather than show it.
    """
    return re.sub(r"\{[^{}]*'status':\s*'[A-Z_]+'[^{}]*\}", "[technical details omitted]", text)
