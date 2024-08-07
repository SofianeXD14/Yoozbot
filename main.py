import telebot
import requests
import threading
import time
from datetime import datetime

# توكن بوت تلغرام
bot = telebot.TeleBot('7326446945:AAFHvL-Qzh9akbfst17MnQhqpIiwWjbn8Bo')

# تخزين الرقم الأخير الذي تم إدخاله ورمز الوصول الأول وتاريخ انتهاء الصلاحية
last_phone_number = {}
access_tokens = {}
otp_codes = {}  # يجب أن يكون هناك خريطة للتوكنات التي تم إرسالها
refresh_tokens = {}  # يجب تخزين رموز التحديث إذا كانت متاحة
access_expiry = {}  # تخزين وقت انتهاء صلاحية رمز الوصول

# إنشاء لوحة مفاتيح مخصصة
def create_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    if last_phone_number:
        btn_phone = telebot.types.KeyboardButton('تغيير رقم الهاتف')
    else:
        btn_phone = telebot.types.KeyboardButton('إرسال رقم الهاتف')
    btn_reset = telebot.types.KeyboardButton('إعادة تعيين')
    btn_update_token = telebot.types.KeyboardButton('تحديث رمز الوصول')
    btn_extend_token = telebot.types.KeyboardButton('تمديد صلاحية الرمز')
    btn_balance = telebot.types.KeyboardButton('عرض رصيد الباقة')
    btn_check_expiry = telebot.types.KeyboardButton('تاريخ انتهاء صلاحية الرمز')
    markup.add(btn_phone, btn_reset, btn_update_token, btn_extend_token, btn_balance, btn_check_expiry)
    return markup

# عند استقبال الأمر /start
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    if chat_id in access_expiry and access_expiry[chat_id] > time.time():
        bot.send_message(chat_id, '🔹 رمز الوصول لا يزال ساري المفعول. اختر إحدى الخيارات:', reply_markup=create_keyboard())
    else:
        bot.send_message(chat_id, '🔹 أهلاً وسهلاً! يرجى إدخال رقم هاتفك:', reply_markup=create_keyboard())
        bot.register_next_step_handler(message, get_phone_number)

# التعامل مع الرسائل النصية
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    chat_id = message.chat.id
    if message.text == 'إرسال رقم الهاتف':
        bot.send_message(chat_id, '🔸 يرجى إدخال رقم هاتفك:')
        bot.register_next_step_handler(message, get_phone_number)
    elif message.text == 'تغيير رقم الهاتف':
        bot.send_message(chat_id, '🔸 يرجى إدخال رقم هاتفك:')
        bot.register_next_step_handler(message, get_phone_number)
    elif message.text == 'إعادة تعيين':
        reset_bot(message)
    elif message.text == 'تحديث رمز الوصول':
        bot.send_message(chat_id, '🔹 جاري تحديث رمز الوصول...')
        update_access_token(message, last_phone_number.get(chat_id))
    elif message.text == 'تمديد صلاحية الرمز':
        bot.send_message(chat_id, '🔹 جاري تمديد صلاحية رمز الوصول...')
        extend_token_manually(message)
    elif message.text == 'عرض رصيد الباقة':
        num = last_phone_number.get(chat_id)
        if num:
            bot.send_message(chat_id, '🔹 جاري الحصول على تفاصيل رصيد الباقة...')
            get_phone_number_balance(chat_id, num)
        else:
            bot.send_message(chat_id, '⚠️ لم يتم إدخال رقم هاتف بعد. يرجى إدخال رقم هاتف أولاً.')
    elif message.text == 'تاريخ انتهاء صلاحية الرمز':
        expiry_date = access_expiry.get(chat_id)
        if expiry_date:
            bot.send_message(chat_id, f'🔹 تاريخ انتهاء صلاحية رمز الوصول: {datetime.fromtimestamp(expiry_date).strftime("%Y-%m-%d %H:%M:%S")}')
        else:
            bot.send_message(chat_id, '⚠️ لم يتم تخزين رمز الوصول بعد. يرجى إدخال الرقم ورمز OTP أولاً.')

# إعادة تعيين البوت
def reset_bot(message):
    last_phone_number.pop(message.chat.id, None)
    access_tokens.pop(message.chat.id, None)
    otp_codes.pop(message.chat.id, None)
    refresh_tokens.pop(message.chat.id, None)
    access_expiry.pop(message.chat.id, None)
    bot.send_message(message.chat.id, '🔄 تم إعادة تعيين البوت.')

# الحصول على رقم الهاتف
def get_phone_number(message):
    num = message.text
    last_phone_number[message.chat.id] = num  # تخزين الرقم
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'ibiza.ooredoo.dz',
        'Connection': 'Keep-Alive',
        'User-Agent': 'okhttp/4.9.3',
    }

    data = {
        'client_id': 'ibiza-app',
        'grant_type': 'password',
        'mobile-number': num,
        'language': 'AR',
    }

    response = requests.post('https://ibiza.ooredoo.dz/auth/realms/ibiza/protocol/openid-connect/token', headers=headers, data=data)

    if 'ROOGY' in response.text:
        bot.send_message(message.chat.id, f'✅ تم إرسال رمز OTP إلى الرقم: {num}.\n🔹 أدخل الرمز:')
        otp_codes[message.chat.id] = num  # تخزين الرقم الذي تم إرسال الرمز إليه
        bot.register_next_step_handler(message, get_otp)
    else:
        bot.send_message(message.chat.id, '⚠️ حدث خطأ، يرجى المحاولة لاحقاً.')

# الحصول على رمز OTP
def get_otp(message):
    otp = message.text
    num = otp_codes.get(message.chat.id)
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'ibiza.ooredoo.dz',
        'Connection': 'Keep-Alive',
        'User-Agent': 'okhttp/4.9.3',
    }

    data = {
        'client_id': 'ibiza-app',
        'otp': otp,
        'grant_type': 'password',
        'mobile-number': num,
        'language': 'AR',
    }

    bot.send_message(message.chat.id, '🔄 جاري التحقق من الرمز، يرجى الانتظار...')

    response = requests.post('https://ibiza.ooredoo.dz/auth/realms/ibiza/protocol/openid-connect/token', headers=headers, data=data)
    
    if response.status_code == 200:
        response_json = response.json()
        access_token = response_json.get('access_token')
        expires_in = response_json.get('expires_in')
        refresh_token = response_json.get('refresh_token')
        if access_token and expires_in:
            access_tokens[message.chat.id] = access_token  # تخزين رمز الوصول
            access_expiry[message.chat.id] = time.time() + expires_in  # تحديث وقت انتهاء الصلاحية
            refresh_tokens[message.chat.id] = refresh_token  # تخزين رمز التحديث إذا كان متاحاً
            bot.send_message(message.chat.id, f'✅ تم التحقق من الرمز بنجاح.\n🔹 تاريخ انتهاء صلاحية رمز الوصول: {datetime.fromtimestamp(access_expiry[message.chat.id]).strftime("%Y-%m-%d %H:%M:%S")}')
            # بدء التمديد التلقائي
            threading.Thread(target=auto_renew_token, args=(message.chat.id,), daemon=True).start()
            # بدء طلب التكفل والتحقق من الرصيد بشكل دوري
            threading.Thread(target=periodic_tasks, args=(message.chat.id,), daemon=True).start()
        else:
            bot.send_message(message.chat.id, '❌ خطأ في التحقق من الرمز.')
    else:
        bot.send_message(message.chat.id, '❌ خطأ في التحقق من الرمز.')

# تمديد صلاحية رمز الوصول تلقائياً
def auto_renew_token(chat_id):
    while True:
        extend_token(chat_id)  # تمديد صلاحية الرمز
        time.sleep(1)  # الانتظار لثانية واحدة قبل التحديث التالي

# تمديد صلاحية رمز الوصول يدوياً
def extend_token_manually(message):
    chat_id = message.chat.id
    extend_token(chat_id)
    bot.send_message(chat_id, '✅ تم تمديد صلاحية الرمز بنجاح.')

# تمديد صلاحية رمز الوصول
def extend_token(chat_id):
    token = access_tokens.get(chat_id)
    if token:
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': 'ibiza.ooredoo.dz',
        }

        data = {
            'client_id': 'ibiza-app',
            'grant_type': 'refresh_token',
            'refresh_token': refresh_tokens.get(chat_id),
            'language': 'AR',
        }

        response = requests.post('https://ibiza.ooredoo.dz/auth/realms/ibiza/protocol/openid-connect/token', headers=headers, data=data)

        if response.status_code == 200:
            response_json = response.json()
            new_access_token = response_json.get('access_token')
            if new_access_token:
                access_tokens[chat_id] = new_access_token  # تحديث رمز الوصول
                access_expiry[chat_id] = time.time() + response_json.get('expires_in', 3600)  # تحديث وقت انتهاء الصلاحية
        # لا ترسل رسالة فشل لأن التمديد التلقائي يتعامل مع الفشل

# إرسال طلب التكفل والتحقق من الرصيد بعد إرسال الطلب بشكل دوري
def periodic_tasks(chat_id):
    while True:
        # إرسال طلب التكفل
        url = 'https://ibiza.ooredoo.dz/api/v1/mobile-bff/users/mgm/info/apply'
        headers = {
            'Authorization': f'Bearer {access_tokens.get(chat_id)}',
            'language': 'AR',
            'request-id': 'ef69f4c6-2ead-4b93-95df-106ef37feefd',
            'flavour-type': 'gms',
            'Content-Type': 'application/json'
        }
        payload = {
            "mgmValue": "ABC"
        }
        for _ in range(6):
            requests.post(url, headers=headers, json=payload)

        # التحقق من الرصيد بعد إرسال طلب التكفل
        head_balance = {
            "Authorization": f'Bearer {access_tokens.get(chat_id)}',
            "language": 'AR',
            "request-id": '46a61a87-8748-49ef-8eec-ce9be28ce0a7',
            "flavour-type": 'gms',
            "Host": 'ibiza.ooredoo.dz',
            "Connection": 'Keep-Alive',
            "User-Agent": 'okhttp/4.9.3'
        }
        response_balance_after = requests.get('https://ibiza.ooredoo.dz/api/v1/mobile-bff/users/balance', headers=head_balance)
        
        if response_balance_after.status_code == 200:
            balance_info_after = response_balance_after.json()
            accounts_after = balance_info_after['accounts']

            account_details_after = "\n".join([
                f"🔸 <b>{account['label']}:</b> <b>{account['value']}</b> (صلاحية: {account['validation']})"
                for account in accounts_after
            ])
            
            balance_message_after = (f'<b>🔹 تفاصيل حسابك بعد إرسال التكفل:</b>\n\n'
                                    f'<b>🔸 رقم الهاتف:</b> {last_phone_number.get(chat_id)}\n\n'
                                    f'{account_details_after}\n\n'
                                    f'🌟 <b>شكراً لاستخدامك خدماتنا!</b>')
            bot.send_message(chat_id, balance_message_after, parse_mode='HTML')
        else:
            bot.send_message(chat_id, '❌ لم نتمكن من التحقق من الرصيد بعد إرسال طلب التكفل.')

        # التوقف لمدة دقيقة بعد التمديد الناجح
        time.sleep(60)

# بدء البوت
bot.polling()
