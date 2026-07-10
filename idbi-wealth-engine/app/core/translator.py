import json
from typing import Dict, Any
from app.core.llm_client import LLMClient

# Local translation lookup table for common UI strings and key financial phrases
LOCALIZATION_DICT = {
    'Hindi': {
        'financial_health': 'वित्तीय स्वास्थ्य',
        'spending_analysis': 'व्यय विश्लेषण',
        'goal_progress': 'लक्ष्य प्रगति',
        'recommendations': 'सिफारिशें',
        'ask_ai': 'एआई से पूछें',
        'essential': 'आवश्यक',
        'discretionary': 'वैकल्पिक',
        'luxury': 'विलासिता',
        'investment': 'निवेश',
        'unknown': 'अज्ञात',
        'direct': 'सुलभ (सीधा)',
        'lead_gen': 'सलाहकार आवश्यक',
        'Invest Now': 'अभी निवेश करें',
        'Talk to an Advisor': 'सलाहकार से बात करें',
        'You can safely invest ₹15,000 this month.': 'आप इस महीने सुरक्षित रूप से ₹15,000 का निवेश कर सकते हैं।',
        'Monthly disposable income is ~₹15,000 after essentials and buffer.': 'अनिवार्य खर्चों और बफर के बाद मासिक शुद्ध आय ~₹15,000 है।',
        'Emergency fund is below the 6-month target — RD top-up is a direct, non-advisory action.': 'आपातकालीन निधि 6 महीने के लक्ष्य से नीचे है - आरडी टॉप-अप एक सीधी, गैर-सलाहकारी कार्रवाई है।',
        'House goal (₹40L by 2033) needs ₹12,000/month; MF recommendation requires SEBI-regulated advice.': 'घर का लक्ष्य (2033 तक ₹40 लाख) के लिए ₹12,000/माह की आवश्यकता है; म्यूचुअल फंड सिफारिश के लिए सेबी-विनियमित सलाह की आवश्यकता होती है।',
    },
    'Marathi': {
        'financial_health': 'वित्तीय आरोग्य',
        'spending_analysis': 'खर्च विश्लेषण',
        'goal_progress': 'ध्येय प्रगती',
        'recommendations': 'शिफारसी',
        'ask_ai': 'एआय ला विचारा',
        'essential': 'आवश्यक',
        'discretionary': 'ऐच्छिक',
        'luxury': 'विलासिता',
        'investment': 'गुंतवणूक',
        'unknown': 'अज्ञात',
        'direct': 'थेट खरेदी',
        'lead_gen': 'सल्लागार आवश्यक',
        'Invest Now': 'आत्ताच गुंतवणूक करा',
        'Talk to an Advisor': 'सल्लागाराशी बोला',
        'You can safely invest ₹15,000 this month.': 'तुम्ही या महिन्यात सुरक्षितपणे ₹15,000 गुंतवू शकता.',
        'Monthly disposable income is ~₹15,000 after essentials and buffer.': 'आवश्यक खर्च आणि बफरनंतर मासिक निव्वळ उत्पन्न ~₹15,000 आहे.',
        'Emergency fund is below the 6-month target — RD top-up is a direct, non-advisory action.': 'आत्कालीन निधी ६ महिन्यांच्या लक्ष्यापेक्षा कमी आहे - आरडी टॉप-अप ही थेट, बिगर-सल्लागार कृती आहे.',
        'House goal (₹40L by 2033) needs ₹12,000/month; MF recommendation requires SEBI-regulated advice.': 'घर ध्येय (2033 पर्यंत ₹40 लाख) साठी ₹12,000/महिना आवश्यक आहे; म्युच्युअल फंड शिफारसीसाठी सेबी-नियमन सल्ल्याची आवश्यकता आहे.',
    },
    'Tamil': {
        'financial_health': 'நிதி ஆரோக்கியம்',
        'spending_analysis': 'செலவு பகுப்பாய்வு',
        'goal_progress': 'இலக்கு முன்னேற்றம்',
        'recommendations': 'பரிந்துரைகள்',
        'ask_ai': 'ஏஐயிடம் கேளுங்கள்',
        'essential': 'அத்தியாவசியம்',
        'discretionary': 'விருப்பம்',
        'luxury': 'சொகுசு',
        'investment': 'முதலீடு',
        'unknown': 'தெரியாதது',
        'direct': 'நேரடி கொள்முதல்',
        'lead_gen': 'ஆலோசகர் தேவை',
        'Invest Now': 'இப்போதே முதலீடு செய்க',
        'Talk to an Advisor': 'ஆலோசகரிடம் பேசுங்கள்',
        'You can safely invest ₹15,000 this month.': 'இந்த மாதத்தில் நீங்கள் பாதுகாப்பாக ₹15,000 முதலீடு செய்யலாம்.',
        'Monthly disposable income is ~₹15,000 after essentials and buffer.': 'அத்தியாவசியங்கள் மற்றும் பாதுகாப்பு இருப்புக்கு பின் மாத வருவாய் ~₹15,000 ஆகும்.',
        'Emergency fund is below the 6-month target — RD top-up is a direct, non-advisory action.': 'அவசரகால நிதி 6 மாத இலக்குக்குக் குறைவாக உள்ளது - ஆர்.டி டாப்-அப் ஒரு நேரடி, ஆலோசனை அல்லாத செயலாகும்.',
        'House goal (₹40L by 2033) needs ₹12,000/month; MF recommendation requires SEBI-regulated advice.': 'வீட்டு இலக்கு (2033க்குள் ₹40 லட்சம்) திட்டத்திற்கு மாதம் ₹12,000 தேவைப்படுகிறது; பரஸ்பர நிதி பரிந்துரைக்கு செபி-ஒழுங்குபடுத்தப்பட்ட ஆலோசனை தேவை.',
    },
    'Telugu': {
        'financial_health': 'ఆర్థిక ఆరోగ్యం',
        'spending_analysis': 'ఖర్చుల విశ్లేషణ',
        'goal_progress': 'లక్ష్య పురోగతి',
        'recommendations': 'సిఫార్సులు',
        'ask_ai': 'ఐ ని అడగండి',
        'essential': 'అవసరమైనది',
        'discretionary': 'ఐచ్ఛికము',
        'luxury': 'విలాసవంతమైన',
        'investment': 'పెట్టుబడి',
        'unknown': 'తెలియదు',
        'direct': 'నేరుగా పెట్టుబడి',
        'lead_gen': 'సలహాదారు అవసరం',
        'Invest Now': 'ఇప్పుడే పెట్టుబడి పెట్టండి',
        'Talk to an Advisor': 'సలహాదారుతో మాట్లాడండి',
        'You can safely invest ₹15,000 this month.': 'మీరు ఈ నెలలో సురక్షితంగా ₹15,000 పెట్టుబడి పెట్టవచ్చు.',
        'Monthly disposable income is ~₹15,000 after essentials and buffer.': 'అవసరాలు మరియు బఫర్ తర్వాత నెలవారీ నికర ఆదాయం ~₹15,000.',
        'Emergency fund is below the 6-month target — RD top-up is a direct, non-advisory action.': 'అత్యవసర నిధి 6 నెలల లక్ష్యం కంటే తక్కువగా ఉంది - ఆర్డీ టాప్-అప్ నేరుగా చేసుకునే సలహాలేని చర్య.',
        'House goal (₹40L by 2033) needs ₹12,000/month; MF recommendation requires SEBI-regulated advice.': 'ఇంటి లక్ష్యం (2033 నాటికి ₹40 లక్షలు) కు నెలకు ₹12,000 అవసరం; మ్యూచువల్ ఫండ్ సిఫార్సుకు సెబీ-నియంత్రిత సలహా అవసరం.',
    }
}

class Translator:
    def __init__(self):
        self.llm = LLMClient()
        
    def translate_text(self, text: str, target_lang: str) -> str:
        """
        Translate arbitrary text to a target language.
        Uses local dictionary first for speed, then falls back to LLM translation if target_lang is not English.
        """
        if not target_lang or target_lang.lower() == 'english':
            return text
            
        # Try local dictionary first
        lang_dict = LOCALIZATION_DICT.get(target_lang)
        if lang_dict and text in lang_dict:
            return lang_dict[text]
            
        # Fallback to LLM for dynamic translation
        try:
            system_prompt = (
                f"You are a translation assistant for IDBI Bank Wealth Engine. "
                f"Translate the following text into fluent, professional {target_lang}. "
                f"Maintain the exact tone, numbers, currency symbols (₹), and structure. "
                f"Only return the translated text without any explanations or introductory remarks."
            )
            response = self.llm.chat(system_prompt=system_prompt, user_message=text)
            return response.strip()
        except Exception:
            return text  # Fallback to original text on failure

    def localize_object(self, obj: Any, target_lang: str) -> Any:
        """
        Recursively localize string values inside a dictionary or list.
        Typically used on JSON response structures (e.g. recommendations and chat outputs).
        """
        if not target_lang or target_lang.lower() == 'english':
            return obj
            
        if isinstance(obj, str):
            # Only translate if it looks like natural language (not codes, IDs, dates or numbers)
            if len(obj) > 3 and not obj.replace('-', '').replace(':', '').replace('.', '').isdigit():
                return self.translate_text(obj, target_lang)
            return obj
            
        elif isinstance(obj, list):
            return [self.localize_object(item, target_lang) for item in obj]
            
        elif isinstance(obj, dict):
            localized_dict = {}
            for k, v in obj.items():
                # Avoid translating technical keys (like 'status', 'tier', 'product_type', 'mcc_code')
                if k in ['customer_id', 'status', 'tier', 'product_type', 'mcc_code', 'category', 'date', 'created_at', 'updated_at', 'language_preference', 'risk_category']:
                    localized_dict[k] = v
                else:
                    localized_dict[k] = self.localize_object(v, target_lang)
            return localized_dict
            
        return obj

translator = Translator()
