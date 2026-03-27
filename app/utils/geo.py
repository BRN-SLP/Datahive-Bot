"""
Geo-language resolution from proxy URLs.

Extracts country code from proxy URL patterns used by major residential/datacenter
proxy providers, then maps to BCP-47 language tags for browser header emulation.

Supported proxy URL patterns:
  - Brightdata:   brd-customer-xxx-country-us:pass@...
  - Smartproxy:   user.country-us:pass@...
  - Oxylabs:      customer-xxx-country-us:pass@...
  - IPRoyal:      user_country-US:pass@...
  - Proxy-Cheap:  user-zone-residential-country-us:pass@...
  - NetNut:       user-country-us:pass@...
  - Infatica:     user-country-US-city-...:pass@...
  - Hostname geo: us.proxy.com, de.proxy.net, proxy-uk-1.host.com
"""

import random
import re
from typing import Tuple

# Country code → (x-user-language, accept-language header value)
# Accept-Language follows real Chrome format:
#   primary locale + base lang at 0.9 + en-US at 0.8 + en at 0.7
# For English locales: just en-US,en;q=0.9
_COUNTRY_LANGUAGE_MAP: dict[str, Tuple[str, str]] = {
    # North America
    'us': ('en-US', 'en-US,en;q=0.9'),
    'ca': ('en-CA', 'en-CA,en;q=0.9,fr-CA;q=0.8,fr;q=0.7'),
    'mx': ('es-MX', 'es-MX,es;q=0.9,en-US;q=0.8,en;q=0.7'),

    # Western Europe
    'gb': ('en-GB', 'en-GB,en;q=0.9'),
    'ie': ('en-IE', 'en-IE,en;q=0.9'),
    'de': ('de-DE', 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7'),
    'at': ('de-AT', 'de-AT,de;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ch': ('de-CH', 'de-CH,de;q=0.9,fr-CH;q=0.8,it-CH;q=0.7,en-US;q=0.6'),
    'fr': ('fr-FR', 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'),
    'nl': ('nl-NL', 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7'),
    'be': ('nl-BE', 'nl-BE,nl;q=0.9,fr-BE;q=0.8,en-US;q=0.7,en;q=0.6'),
    'es': ('es-ES', 'es-ES,es;q=0.9,en-US;q=0.8,en;q=0.7'),
    'pt': ('pt-PT', 'pt-PT,pt;q=0.9,en-US;q=0.8,en;q=0.7'),
    'it': ('it-IT', 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'),
    'lu': ('fr-LU', 'fr-LU,fr;q=0.9,de-LU;q=0.8,en-US;q=0.7'),

    # Nordic
    'se': ('sv-SE', 'sv-SE,sv;q=0.9,en-US;q=0.8,en;q=0.7'),
    'no': ('nb-NO', 'nb-NO,nb;q=0.9,en-US;q=0.8,en;q=0.7'),
    'dk': ('da-DK', 'da-DK,da;q=0.9,en-US;q=0.8,en;q=0.7'),
    'fi': ('fi-FI', 'fi-FI,fi;q=0.9,en-US;q=0.8,en;q=0.7'),

    # Eastern Europe / CIS
    'ua': ('uk-UA', 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7'),
    'pl': ('pl-PL', 'pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7'),
    'cz': ('cs-CZ', 'cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7'),
    'sk': ('sk-SK', 'sk-SK,sk;q=0.9,cs-CZ;q=0.8,en-US;q=0.7'),
    'hu': ('hu-HU', 'hu-HU,hu;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ro': ('ro-RO', 'ro-RO,ro;q=0.9,en-US;q=0.8,en;q=0.7'),
    'bg': ('bg-BG', 'bg-BG,bg;q=0.9,en-US;q=0.8,en;q=0.7'),
    'rs': ('sr-RS', 'sr-RS,sr;q=0.9,en-US;q=0.8,en;q=0.7'),
    'hr': ('hr-HR', 'hr-HR,hr;q=0.9,en-US;q=0.8,en;q=0.7'),
    'si': ('sl-SI', 'sl-SI,sl;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ee': ('et-EE', 'et-EE,et;q=0.9,en-US;q=0.8,en;q=0.7'),
    'lv': ('lv-LV', 'lv-LV,lv;q=0.9,en-US;q=0.8,en;q=0.7'),
    'lt': ('lt-LT', 'lt-LT,lt;q=0.9,en-US;q=0.8,en;q=0.7'),
    'by': ('be-BY', 'be-BY,be;q=0.9,ru-RU;q=0.8,ru;q=0.7'),
    'md': ('ro-MD', 'ro-MD,ro;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ru': ('ru-RU', 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'),
    'kz': ('ru-KZ', 'ru-KZ,ru;q=0.9,kk-KZ;q=0.8,en-US;q=0.7'),

    # Asia Pacific
    'au': ('en-AU', 'en-AU,en;q=0.9'),
    'nz': ('en-NZ', 'en-NZ,en;q=0.9'),
    'jp': ('ja-JP', 'ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7'),
    'kr': ('ko-KR', 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'),
    'cn': ('zh-CN', 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7'),
    'tw': ('zh-TW', 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7'),
    'hk': ('zh-HK', 'zh-HK,zh;q=0.9,en-US;q=0.8,en;q=0.7'),
    'sg': ('en-SG', 'en-SG,en;q=0.9,zh-SG;q=0.8,zh;q=0.7'),
    'in': ('en-IN', 'en-IN,en;q=0.9,hi-IN;q=0.8,hi;q=0.7'),
    'id': ('id-ID', 'id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7'),
    'th': ('th-TH', 'th-TH,th;q=0.9,en-US;q=0.8,en;q=0.7'),
    'vn': ('vi-VN', 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ph': ('en-PH', 'en-PH,en;q=0.9,fil-PH;q=0.8'),
    'my': ('ms-MY', 'ms-MY,ms;q=0.9,en-US;q=0.8,en;q=0.7'),

    # Middle East / Africa
    'tr': ('tr-TR', 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7'),
    'il': ('he-IL', 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ae': ('ar-AE', 'ar-AE,ar;q=0.9,en-US;q=0.8,en;q=0.7'),
    'sa': ('ar-SA', 'ar-SA,ar;q=0.9,en-US;q=0.8,en;q=0.7'),
    'za': ('en-ZA', 'en-ZA,en;q=0.9,af-ZA;q=0.8'),

    # Latin America
    'br': ('pt-BR', 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'),
    'ar': ('es-AR', 'es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7'),
    'co': ('es-CO', 'es-CO,es;q=0.9,en-US;q=0.8,en;q=0.7'),
    'cl': ('es-CL', 'es-CL,es;q=0.9,en-US;q=0.8,en;q=0.7'),
    'pe': ('es-PE', 'es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7'),
}

def _random_language() -> Tuple[str, str]:
    """Return a random (x_user_language, accept_language) pair from the map."""
    return random.choice(list(_COUNTRY_LANGUAGE_MAP.values()))

# Ordered patterns to try for country code extraction (most specific first)
# All match a 2-letter ISO country code after a known keyword/separator
_PROXY_COUNTRY_PATTERNS = [
    # Keyword-based (major providers)
    r'[-_.]country[-_.]([a-z]{2})',          # country-us, country_us, .country.us
    r'[-_.]cc[-_.]([a-z]{2})',               # -cc-us, _cc_us
    r'[-_.]nation[-_.]([a-z]{2})',           # -nation-us
    r'country=([a-z]{2})',                   # country=us (query param style)
    r'[-_]geo[-_]([a-z]{2})',               # -geo-us

    # Hostname prefix/suffix patterns
    r'^(?:https?://)?(?:[^@]+@)?([a-z]{2})\d*\.(?:proxy|gate|gw|exit)',  # us1.proxy.com
    r'\.([a-z]{2})[-.](?:proxy|gate|gw|exit|node|peer)',                  # .us.gate.net

    # Provider-specific last resort: 2-letter word boundary in username part
    r'(?:^|[-_.:/])([a-z]{2})(?:[-_.]|$)',   # broad catch — lower priority
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _PROXY_COUNTRY_PATTERNS]


def _extract_country_code(proxy: str) -> str | None:
    """
    Extract ISO 3166-1 alpha-2 country code from a proxy URL string.
    Returns lowercase country code or None if not found.
    """
    if not proxy:
        return None

    # Work on the full proxy string lowercased
    proxy_lower = proxy.lower()

    for pattern in _COMPILED_PATTERNS:
        match = pattern.search(proxy_lower)
        if match:
            code = match.group(1).lower()
            if code in _COUNTRY_LANGUAGE_MAP:
                return code

    return None


def proxy_to_language(proxy: str | None) -> Tuple[str, str]:
    """
    Derive browser language settings from a proxy URL.

    Returns:
        (x_user_language, accept_language)
        e.g. ('en-US', 'en-US,en;q=0.9') for a US proxy
             random entry from the map if proxy is missing or country undetectable
    """
    if not proxy:
        return _random_language()

    code = _extract_country_code(proxy)
    if code and code in _COUNTRY_LANGUAGE_MAP:
        return _COUNTRY_LANGUAGE_MAP[code]

    return _random_language()
