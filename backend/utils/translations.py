"""Lightweight UI translation for the public storefront. Only the site
"chrome" (nav, buttons, common labels) is translated -- a vendor's own
product names, descriptions, story, etc. stay exactly as they wrote them.
"""

TRANSLATIONS = {
    "Home": {"hi": "होम"},
    "Products": {"hi": "प्रोडक्ट्स"},
    "Custom Order": {"hi": "कस्टम ऑर्डर"},
    "My Orders": {"hi": "मेरे ऑर्डर"},
    "Wishlist": {"hi": "विशलिस्ट"},
    "About Us": {"hi": "हमारे बारे में"},
    "Contact": {"hi": "संपर्क करें"},
    "Explore Products": {"hi": "प्रोडक्ट्स देखें"},
    "Order Now": {"hi": "अभी ऑर्डर करें"},
    "Add to Cart": {"hi": "कार्ट में डालें"},
    "Confirm Order": {"hi": "ऑर्डर कन्फर्म करें"},
    "Find Orders": {"hi": "ऑर्डर खोजें"},
    "Quick Links": {"hi": "जरूरी लिंक"},
    "Our Products": {"hi": "हमारे प्रोडक्ट्स"},
    "Search products...": {"hi": "प्रोडक्ट खोजें..."},
    "Categories": {"hi": "कैटेगरी"},
    "All Products": {"hi": "सभी प्रोडक्ट्स"},
    "Sort By": {"hi": "क्रमबद्ध करें"},
    "In Stock": {"hi": "स्टॉक में है"},
    "Out of Stock": {"hi": "स्टॉक में नहीं है"},
    "Write a Review": {"hi": "रिव्यू लिखें"},
    "Customer Reviews": {"hi": "ग्राहकों की समीक्षा"},
    "Full Name": {"hi": "पूरा नाम"},
    "Mobile Number": {"hi": "मोबाइल नंबर"},
    "Quantity": {"hi": "मात्रा"},
    "Delivery Address": {"hi": "डिलीवरी का पता"},
}


def translate(text, lang):
    if lang == "hi" and text in TRANSLATIONS:
        return TRANSLATIONS[text].get("hi", text)
    return text
