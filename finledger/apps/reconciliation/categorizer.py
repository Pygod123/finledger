"""
Auto-Categorizer
----------------
Rule-based categorization of transaction narrations.
Rules are checked in priority order; first match wins.
"""

CATEGORY_RULES = [
    # (category_name, [keywords...])
    ('Food & Dining',    ['swiggy', 'zomato', 'mcdonalds', 'dominos', 'kfc', 'pizza',
                          'subway', 'burger king', 'haldirams', 'cafe', 'restaurant',
                          'food', 'bakery', 'barbeque', 'biryani']),

    ('Travel',           ['uber', 'ola', 'rapido', 'irctc', 'indigo', 'spicejet',
                          'air india', 'makemytrip', 'goibibo', 'yatra', 'redbus',
                          'metro', 'petrol', 'fuel', 'toll', 'fastag', 'parking']),

    ('SaaS & Software',  ['aws', 'amazon web', 'azure', 'google cloud', 'gcp',
                          'digitalocean', 'github', 'gitlab', 'jira', 'atlassian',
                          'notion', 'slack', 'zoom', 'figma', 'canva', 'adobe',
                          'netflix', 'spotify', 'hotstar', 'youtube premium',
                          'copilot', 'vercel', 'heroku', 'cloudflare']),

    ('Utilities',        ['electricity', 'bsnl', 'jio', 'airtel', 'vodafone', 'vi',
                          'broadband', 'internet', 'water bill', 'gas bill',
                          'maintenance', 'society', 'postpaid', 'recharge']),

    ('Healthcare',       ['apollo', 'medplus', 'pharmeasy', 'netmeds', 'hospital',
                          'clinic', 'doctor', 'pharmacy', 'medicine', 'insurance',
                          'health', 'diagnostic', 'lab test', 'pathology']),

    ('Shopping',         ['amazon', 'flipkart', 'myntra', 'ajio', 'meesho',
                          'reliance', 'nykaa', 'shoppers stop', 'shopping',
                          'mall', 'retail', 'store']),

    ('Banking & Finance', ['emi', 'loan', 'interest', 'credit card', 'hdfc',
                           'icici', 'sbi', 'axis', 'kotak', 'idfc', 'bank',
                           'neft', 'rtgs', 'imps', 'upi', 'payment gateway',
                           'razorpay', 'payu', 'cashfree']),

    ('Revenue',          ['salary', 'client payment', 'invoice', 'consulting',
                          'freelance', 'income', 'receipt', 'transfer in',
                          'refund', 'cashback']),

    ('Education',        ['udemy', 'coursera', 'unacademy', 'byju', 'vedantu',
                          'school', 'college', 'university', 'fees', 'tuition']),

    ('Entertainment',    ['bookmyshow', 'pvr', 'inox', 'movie', 'event',
                          'concert', 'gaming', 'steam', 'playstation']),
]

_DEFAULT = 'Others'


def categorize(narration: str) -> str:
    """Return the best-matching category for a narration string."""
    lower = narration.lower()
    for category, keywords in CATEGORY_RULES:
        if any(kw in lower for kw in keywords):
            return category
    return _DEFAULT


def get_all_categories() -> list[str]:
    """Return all defined category names plus default."""
    return [c for c, _ in CATEGORY_RULES] + [_DEFAULT]
